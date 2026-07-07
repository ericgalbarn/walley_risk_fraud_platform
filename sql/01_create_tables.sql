-- =============================================
-- DATABASE: walley_risk_db
-- SCHEMA: public
-- DESCRIPTION: Complete table structure for Walley Risk Decision Platform
-- VERSION: 1.0
-- DATE: 2026-07-03
-- =============================================

-- =============================================
-- TABLE: users
-- Description: Stores account holder information and static profile data.
-- Note: Contains PII. Encrypt at rest in production.
-- =============================================

CREATE TABLE users (
    -- Primary Key
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Personal Information (PII)
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL UNIQUE,
    
    -- Financial & Account Data
    wallet_balance DECIMAL(15,2) NOT NULL DEFAULT 0.00 CHECK (wallet_balance >= 0),
    
    -- Location Data
    home_city VARCHAR(50),
    home_country VARCHAR(50),
    
    -- Audit & Status Fields
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_timestamp TIMESTAMP,
    
    -- Risk & Compliance Fields
    kyc_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (kyc_status IN ('pending', 'verified', 'rejected', 'expired')),
    risk_tier VARCHAR(10) DEFAULT 'low' CHECK (risk_tier IN ('low', 'medium', 'high')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Performance Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_kyc_status ON users(kyc_status);


-- =============================================
-- TABLE: beneficiaries
-- Description: Stores recipient (beneficiary) information. 
-- Used to track mule accounts and money laundering rings.
-- =============================================

CREATE TABLE beneficiaries (
    -- Primary Key
    beneficiary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Beneficiary Information (PII)
    beneficiary_name VARCHAR(100) NOT NULL,
    beneficiary_phone VARCHAR(20),
    beneficiary_bank_account VARCHAR(50),
    beneficiary_country VARCHAR(50) NOT NULL,
    
    -- Audit Fields
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Compliance & Verification
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Derived / Aggregated Stats (Pre-computed for performance)
    total_transactions_received INTEGER NOT NULL DEFAULT 0,
    unique_senders_count INTEGER NOT NULL DEFAULT 0,
    first_transaction_date TIMESTAMP,
    last_transaction_date TIMESTAMP
);

-- Performance Indexes
CREATE INDEX idx_beneficiaries_name ON beneficiaries(beneficiary_name);
CREATE INDEX idx_beneficiaries_country ON beneficiaries(beneficiary_country);
CREATE INDEX idx_beneficiaries_created ON beneficiaries(created_at);


-- =============================================
-- TABLE: device_authentications
-- Description: Stores login events and device fingerprinting data.
-- Critical for detecting device anomalies associated with Account Takeover.
-- =============================================

CREATE TABLE device_authentications (
    -- Primary Key
    auth_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign Key
    user_id UUID NOT NULL,
    
    -- Device Fingerprint (Hashed for privacy)
    device_id VARCHAR(255) NOT NULL, -- e.g., FingerprintJS hash
    
    -- Login Event Data
    login_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Geolocation (Derived from IP)
    ip_geolocation_country VARCHAR(50),
    ip_geolocation_city VARCHAR(50),
    
    -- Risk Signals (Derived)
    is_proxy_vpn BOOLEAN NOT NULL DEFAULT FALSE,
    is_emulator BOOLEAN NOT NULL DEFAULT FALSE,
    is_suspicious_login BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Device Metadata
    os_type VARCHAR(20),
    browser_fingerprint VARCHAR(255),
    
    -- Session Analytics (Derived)
    session_duration_minutes INTEGER, -- NULL if session is active
    
    -- Foreign Key Constraint
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Performance Indexes (Critical for speed)
CREATE INDEX idx_device_auth_user_id ON device_authentications(user_id);
CREATE INDEX idx_device_auth_login_time ON device_authentications(login_timestamp DESC);
CREATE INDEX idx_device_auth_device_id ON device_authentications(device_id);
CREATE INDEX idx_device_auth_suspicious ON device_authentications(is_suspicious_login);


-- =============================================
-- TABLE: transactions
-- Description: Stores all P2P transfer transactions and their risk decisions.
-- This is the core table for fraud detection and analytics.
-- =============================================

CREATE TABLE transactions (
    -- Primary Key
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign Keys
    user_id UUID NOT NULL,
    beneficiary_id UUID NOT NULL,
    
    -- Core Transaction Data
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Risk Decision Fields
    fraud_score DECIMAL(5,4),  -- NULL if ML model hasn't run yet
    final_decision VARCHAR(20) NOT NULL DEFAULT 'pending',
    reviewed_by VARCHAR(50),
    reviewed_at TIMESTAMP,
    rule_flags TEXT[],  -- Array of rule names triggered
    
    -- Derived Features (Pre-computed)
    transaction_balance_ratio DECIMAL(5,4),  -- NULL if balance = 0
    is_beneficiary_new BOOLEAN NOT NULL DEFAULT TRUE,
    is_off_hours BOOLEAN NOT NULL DEFAULT FALSE,
    is_weekend BOOLEAN NOT NULL DEFAULT FALSE,
    distance_from_home_km DECIMAL(8,2) NOT NULL,
    user_7day_transaction_count INTEGER NOT NULL DEFAULT 0,
    is_new_device BOOLEAN NOT NULL DEFAULT TRUE,
    beneficiary_account_age_days INTEGER NOT NULL DEFAULT 0,
    time_since_last_login_minutes INTEGER,  -- NULL if no login history
    is_high_risk_country BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Foreign Key Constraints
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (beneficiary_id) REFERENCES beneficiaries(beneficiary_id)
);

-- Performance Indexes
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_timestamp ON transactions(timestamp DESC);
CREATE INDEX idx_transactions_status ON transactions(status);