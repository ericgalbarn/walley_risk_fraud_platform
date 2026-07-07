------Update users' null timestamp-----------
UPDATE users
SET created_at = '2026-01-01 00:00:00'
WHERE created_at IS NULL; 

UPDATE users
SET last_login_timestamp = '2026-01-01 00:00:00'
WHERE last_login_timestamp IS NULL; 

------Update transactions' null timestamp-----------
UPDATE transactions
SET timestamp = '2026-01-01 00:00:00'
WHERE timestamp IS NULL; 

UPDATE transactions
SET reviewed_at = '2026-01-01 00:00:00'
WHERE reviewed_at IS NULL; 

------Update device authentications' null timestamp-----------
UPDATE device_authentications
SET login_timestamp = '2026-01-01 00:00:00'
WHERE login_timestamp IS NULL; 

------Update beneficiaries' null timestamp-----------
UPDATE beneficiaries
SET created_at = '2026-01-01 00:00:00'
WHERE created_at IS NULL; 

UPDATE beneficiaries
SET first_transaction_date = '2026-01-01 00:00:00'
WHERE first_transaction_date IS NULL; 

UPDATE beneficiaries
SET last_transaction_date = '2026-01-01 00:00:00'
WHERE last_transaction_date IS NULL;
