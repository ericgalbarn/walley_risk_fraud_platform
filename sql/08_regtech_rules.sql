-- =============================================
-- REGTECH LAYER: COMPLETE RULE SET
-- Purpose: Implement AML & Fraud Detection Rules
-- Compliance: SBV Decision 2345, FATF Guidelines
-- =============================================

-- =============================================
-- SCHEMA SETUP (Run Once)
-- =============================================

-- Add merchant_country column for cross-border detection
ALTER TABLE transactions 
ADD COLUMN IF NOT EXISTS merchant_country VARCHAR(50);

-- Add geolocation columns for impossible travel detection
ALTER TABLE device_authentications 
ADD COLUMN IF NOT EXISTS ip_latitude DECIMAL(10,6),
ADD COLUMN IF NOT EXISTS ip_longitude DECIMAL(10,6);

-- Create view for login history analysis
CREATE OR REPLACE VIEW user_login_history AS
SELECT 
    user_id,
    login_timestamp,
    ip_latitude,
    ip_longitude,
    LAG(login_timestamp) OVER (PARTITION BY user_id ORDER BY login_timestamp) AS prev_login_timestamp,
    LAG(ip_latitude) OVER (PARTITION BY user_id ORDER BY login_timestamp) AS prev_ip_latitude,
    LAG(ip_longitude) OVER (PARTITION BY user_id ORDER BY login_timestamp) AS prev_ip_longitude
FROM device_authentications;

-- =============================================
-- RULE 1: BIOMETRIC STRUCTURING
-- Risk Intent: Detect transactions structured just below the 10M VND biometric threshold
-- Compliance: SBV Decision 2345 (Biometric Authentication)
-- Pattern: 9M-9.99M + New Beneficiary + High-Risk Country
-- =============================================

UPDATE transactions
SET rule_flags = array_append(rule_flags, 'biometric_structuring_rule')
WHERE amount BETWEEN 9000000 AND 9999999
  AND is_beneficiary_new = TRUE
  AND beneficiary_id IN (
      SELECT beneficiary_id
      FROM beneficiaries
      WHERE beneficiary_country IN ('North Korea', 'Iran', 'Syria', 'Myanmar', 'Russia')
  );

-- =============================================
-- RULE 2: CASH-OUT VELOCITY (ATO BURST DETECTION)
-- Risk Intent: Detect high-frequency transactions within ultra-short windows
-- Pattern: >3 transactions within a rolling 5-minute window
-- =============================================

WITH burst_transactions AS (
    SELECT 
        transaction_id,
        COUNT(*) OVER (
            PARTITION BY user_id 
            ORDER BY timestamp 
            RANGE BETWEEN INTERVAL '5 MINUTES' PRECEDING AND CURRENT ROW
        ) AS txn_count_5min
    FROM transactions
)
UPDATE transactions
SET rule_flags = array_append(rule_flags, 'velocity_rule')
WHERE transaction_id IN (
    SELECT transaction_id 
    FROM burst_transactions 
    WHERE txn_count_5min > 3
);

-- =============================================
-- RULE 3: CROSS-BORDER CARD FRAUD
-- Risk Intent: Detect international merchant payments to FATF high-risk countries
-- Pattern: Merchant country in FATF blacklist + Amount > 1M VND
-- =============================================

UPDATE transactions
SET rule_flags = array_append(rule_flags, 'cross_border_fraud_rule')
WHERE merchant_country IN ('North Korea', 'Iran', 'Syria', 'Myanmar', 'Russia')
  AND amount > 1000000;

-- =============================================
-- RULE 4: BIOMETRIC EVASION
-- Risk Intent: Detect first-time transfers just below the biometric threshold
-- Pattern: 9M-9.99M + New Beneficiary
-- =============================================

UPDATE transactions
SET rule_flags = array_append(rule_flags, 'biometric_evasion_rule')
WHERE amount BETWEEN 9000000 AND 9999999
  AND is_beneficiary_new = TRUE;

-- =============================================
-- RULE 5: IMPOSSIBLE TRAVEL (ATO BEHAVIORAL FLAG)
-- Risk Intent: Detect login from a new device with impossible geolocation
-- Pattern: New device + Amount >= 10M + Two logins >100km apart within 2 hours
-- =============================================

UPDATE transactions t
SET rule_flags = array_append(rule_flags, 'impossible_travel_rule')
WHERE t.is_new_device = TRUE
  AND t.amount >= 10000000
  AND EXISTS (
      SELECT 1 
      FROM user_login_history l
      WHERE l.user_id = t.user_id
        AND l.login_timestamp <= t.timestamp
        AND l.prev_login_timestamp IS NOT NULL
        AND ( 
            -- Approximate distance > 100 km (using squared difference)
            ( 
                (l.ip_latitude - l.prev_ip_latitude) ^ 2 +
                (l.ip_longitude - l.prev_ip_longitude) ^ 2
            ) > 1.0
            -- Time difference less than 2 hours
            AND EXTRACT(EPOCH FROM (l.login_timestamp - l.prev_login_timestamp)) / 3600 < 2
        )
  );

-- =============================================
-- VERIFICATION QUERY
-- Preview how many transactions each rule flagged
-- =============================================

SELECT 
    unnest(rule_flags) AS rule_name,
    COUNT(*) AS triggered_count
FROM transactions
WHERE rule_flags IS NOT NULL
GROUP BY rule_name
ORDER BY triggered_count DESC;