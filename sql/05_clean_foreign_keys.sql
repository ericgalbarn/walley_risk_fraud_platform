DELETE FROM transactions
WHERE beneficiary_id NOT IN (SELECT beneficiary_id FROM beneficiaries);