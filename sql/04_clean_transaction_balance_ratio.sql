UPDATE transactions
SET transaction_balance_ratio = 0.0
WHERE transaction_balance_ratio IS NULL;
