UPDATE transactions
SET distance_from_home_km = 0.0
WHERE distance_from_home_km IS NULL OR distance_from_home_km < 0;