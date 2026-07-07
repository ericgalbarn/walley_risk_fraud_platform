-------Fixing negative amounts of users' data to absolute numerical values----------

UPDATE users
SET wallet_balance = ABS(wallet_balance)
WHERE wallet_balance < 0;

-------Fixing negative amounts of transactions' data to absolute numerical values----------

UPDATE transactions
SET amount = ABS(amount)
WHERE amount < 0;

UPDATE transactions
SET fraud_score = ABS(fraud_score)
WHERE fraud_score < 0;

UPDATE transactions
SET transaction_balance_ratio = ABS(transaction_balance_ratio)
WHERE transaction_balance_ratio < 0;

UPDATE transactions
SET distance_from_home_km = ABS(distance_from_home_km)
WHERE distance_from_home_km < 0;

UPDATE transactions
SET user_7day_transaction_count = ABS(user_7day_transaction_count)
WHERE user_7day_transaction_count < 0;

UPDATE transactions
SET beneficiary_account_age_days = ABS(beneficiary_account_age_days)
WHERE beneficiary_account_age_days < 0;

UPDATE transactions
SET time_since_last_login_minutes = ABS(time_since_last_login_minutes)
WHERE time_since_last_login_minutes < 0;

-------Fixing negative amounts of beneficiaries' data to absolute numerical values----------

UPDATE beneficiaries
SET total_transactions_received = ABS(total_transactions_received)
WHERE total_transactions_received < 0;

UPDATE beneficiaries
SET unique_senders_count = ABS(unique_senders_count)
WHERE unique_senders_count < 0;

-------Fixing negative amounts of device authentications' data to absolute numerical values----------

UPDATE device_authentications
SET session_duration_minutes = ABS(session_duration_minutes)
WHERE session_duration_minutes < 0;
