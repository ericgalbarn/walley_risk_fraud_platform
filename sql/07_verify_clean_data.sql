------Verify Null Timestamps-------
SELECT 
    'NULL Timestamps' AS Check_Name,
    (SELECT COUNT(*) FROM users WHERE created_at IS NULL) AS users_created_at,
    (SELECT COUNT(*) FROM users WHERE last_login_timestamp IS NULL) AS users_last_login,
    (SELECT COUNT(*) FROM transactions WHERE timestamp IS NULL) AS transactions_timestamp,
    (SELECT COUNT(*) FROM transactions WHERE reviewed_at IS NULL) AS transactions_reviewed_at,
    (SELECT COUNT(*) FROM device_authentications WHERE login_timestamp IS NULL) AS device_auth_login,
    (SELECT COUNT(*) FROM beneficiaries WHERE created_at IS NULL) AS beneficiaries_created_at,
    (SELECT COUNT(*) FROM beneficiaries WHERE first_transaction_date IS NULL) AS beneficiaries_first_txn,
    (SELECT COUNT(*) FROM beneficiaries WHERE last_transaction_date IS NULL) AS beneficiaries_last_txn;

------Verify Negative Amounts-------
SELECT 
    'Negative Amounts' AS Check_Name,
    COUNT(*) AS Negative_Count
FROM transactions 
WHERE amount < 0;

------Verify Null Transaction Balance Ratio-------
SELECT 
    'NULL Balance Ratio' AS Check_Name,
    COUNT(*) AS Null_Count
FROM transactions 
WHERE transaction_balance_ratio IS NULL;

------Verify Foreign Keys-------
SELECT 
    'Broken Foreign Keys' AS Check_Name,
    COUNT(*) AS Orphan_Count
FROM transactions 
WHERE beneficiary_id NOT IN (SELECT beneficiary_id FROM beneficiaries);

------Verify Distances-------

SELECT 
    'Invalid Distances' AS Check_Name,
    COUNT(*) AS Negative_Count
FROM transactions 
WHERE distance_from_home_km < 0 OR distance_from_home_km IS NULL;

------Clean total summary-------
SELECT 
    '=== ALL CLEANING COMPLETE ===' AS Summary_Status,
    NOW() AS Verification_Date,
    (SELECT COUNT(*) FROM transactions) AS Total_Transactions,
    (SELECT COUNT(*) FROM users) AS Total_Users,
    (SELECT COUNT(*) FROM beneficiaries) AS Total_Beneficiaries,
    (SELECT COUNT(*) FROM device_authentications) AS Total_Devices;

------Preview 10 random transactions-------
SELECT 
    transaction_id,
    user_id,
    amount,
    timestamp,
    transaction_balance_ratio,
    distance_from_home_km,
    is_beneficiary_new,
    is_off_hours,
    fraud_score,
    final_decision
FROM transactions
ORDER BY RANDOM()
LIMIT 10;