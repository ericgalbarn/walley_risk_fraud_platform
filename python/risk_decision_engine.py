# =============================================
# Phase 12: Risk Decision Engine
# =============================================

import psycopg2
import pandas as pd
import numpy as np
import json
import xgboost as xgb
import shap
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# =============================================
# Configuration
# =============================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "walley_risk_db",
    "user": "postgres",
    "password": "minhduc2004" 
}

# Dynamic thresholds based on user risk tier
THRESHOLD_MAP = {
    'low': 0.30,      # VIP users: more lenient
    'medium': 0.25,   # Standard users
    'high': 0.15      # High-risk users: stricter
}

# =============================================
# Load Model & Threshold
# =============================================

print("Loading model and threshold...")

# Load XGBoost model
model = xgb.XGBClassifier()
model.load_model('fraud_model.json')

# Load optimal threshold
with open('optimal_threshold.json', 'r') as f:
    config = json.load(f)
    default_threshold = config['threshold']

print(f"✅ Model loaded. Default threshold: {default_threshold:.4f}")

# =============================================
# Connect to Database
# =============================================

print("Connecting to database...")
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

# =============================================
# Fetch Unprocessed Transactions
# =============================================

print("Fetching unprocessed transactions...")

query = """
SELECT 
    t.transaction_id,
    t.user_id,
    t.amount,
    t.transaction_balance_ratio,
    t.distance_from_home_km,
    t.user_7day_transaction_count,
    t.beneficiary_account_age_days,
    t.time_since_last_login_minutes,
    t.is_beneficiary_new,
    t.is_off_hours,
    t.is_weekend,
    t.is_new_device,
    t.is_high_risk_country,
    t.rule_flags,
    u.risk_tier,
    u.wallet_balance
FROM transactions t
LEFT JOIN users u ON t.user_id = u.user_id
WHERE t.fraud_score IS NULL 
  AND t.status != 'blocked'
LIMIT 1000;  -- Process in batches to avoid memory issues
"""

df = pd.read_sql(query, conn)
print(f"✅ Fetched {len(df)} transactions to process.")

if len(df) == 0:
    print("No new transactions to process. Exiting.")
    cursor.close()
    conn.close()
    exit()

# =============================================
# Prepare Features for Scoring
# =============================================

print("Preparing features for scoring...")

# Features in the same order as training
feature_columns = [
    'amount', 
    'transaction_balance_ratio',
    'distance_from_home_km',
    'user_7day_transaction_count',
    'beneficiary_account_age_days',
    'time_since_last_login_minutes',
    'is_beneficiary_new',
    'is_off_hours',
    'is_weekend',
    'is_new_device',
    'is_high_risk_country'
]

# Ensure all columns exist and fill NaN with 0
X = df[feature_columns].fillna(0)

# =============================================
# Score Transactions
# =============================================

print("Scoring transactions...")
df['ml_score'] = model.predict_proba(X)[:, 1]

# =============================================
# Apply Dynamic Thresholding
# =============================================

print("Applying dynamic thresholds...")

def get_threshold(risk_tier):
    """Return threshold based on user risk tier."""
    if risk_tier in THRESHOLD_MAP:
        return THRESHOLD_MAP[risk_tier]
    return default_threshold

df['threshold'] = df['risk_tier'].apply(get_threshold)

# =============================================
# Decision Logic
# =============================================

print("Applying decision logic...")

def make_decision(row):
    """
    Decision logic:
    - If ANY RegTech rule is triggered -> BLOCK
    - Else if ML score > threshold -> REVIEW
    - Else -> APPROVE
    """
    # Check RegTech override
    if row['rule_flags'] and len(row['rule_flags']) > 0:
        return 'block'
    
    # ML-based decision
    if row['ml_score'] > row['threshold']:
        return 'review'
    else:
        return 'approve'

df['final_decision'] = df.apply(make_decision, axis=1)

print(f"✅ Decisions made:")
print(f"   - Approve: {(df['final_decision'] == 'approve').sum()}")
print(f"   - Review:  {(df['final_decision'] == 'review').sum()}")
print(f"   - Block:   {(df['final_decision'] == 'block').sum()}")

# =============================================
# Generate SHAP Explanations (For Review Cases)
# =============================================

print("Generating SHAP explanations for review cases...")

# Prepare background data with proper types
background_data = X.sample(min(100, len(X)), random_state=42)

# Ensure all data is float64 (SHAP requirement)
background_data = background_data.astype(np.float64)
X_for_shap = X.astype(np.float64)

# Create SHAP explainer
explainer = shap.TreeExplainer(model, background_data)

def get_shap_explanation(row):
    """Return SHAP explanation as a dictionary of top features."""
    if row['final_decision'] != 'review':
        return None
    
    # Prepare feature vector with proper dtype
    feature_vector = row[feature_columns].fillna(0).astype(np.float64).values.reshape(1, -1)
    shap_values = explainer.shap_values(feature_vector)
    
    # Get top features (absolute values)
    shap_abs = np.abs(shap_values[0])
    top_indices = np.argsort(shap_abs)[-3:][::-1]  # Top 3 features
    
    explanation = {}
    for idx in top_indices:
        feature_name = feature_columns[idx]
        explanation[feature_name] = float(shap_values[0][idx])
    
    return explanation

# Apply SHAP explanation (only for review cases)
df['shap_explanation'] = df.apply(get_shap_explanation, axis=1)

print(f"✅ SHAP explanations generated for {df['shap_explanation'].notna().sum()} review cases.")

# =============================================
# Write Audit Log
# =============================================

print("Writing audit log...")

# Create audit log DataFrame
audit_log = df[['transaction_id', 'user_id', 'ml_score', 'threshold', 
                'final_decision', 'risk_tier', 'rule_flags', 'shap_explanation']].copy()
audit_log['timestamp'] = datetime.now()
audit_log['model_version'] = 'fraud_model_v1'

# Save audit log to CSV
audit_log.to_csv('audit_log.csv', index=False)
print(f"✅ Audit log saved to 'audit_log.csv' ({len(audit_log)} records)")

# =============================================
# Update Database
# =============================================

print("Updating database...")

# Update transactions table with fraud_score and final_decision
updated_count = 0
for _, row in df.iterrows():
    cursor.execute("""
        UPDATE transactions
        SET fraud_score = %s,
            final_decision = %s,
            status = %s
        WHERE transaction_id = %s
    """, (
        round(row['ml_score'], 4),
        row['final_decision'],
        row['final_decision'],
        row['transaction_id']
    ))
    updated_count += 1

conn.commit()
print(f"✅ Updated {updated_count} transactions in the database.")

# =============================================
# Summary Report
# =============================================

print("\n" + "="*60)
print("Risk Decision Engine Summary")
print("="*60)

# Count by final decision
print("\n📊 Final Decisions:")
print(f"   ✅ Approve: {(df['final_decision'] == 'approve').sum()}")
print(f"   🔍 Review:  {(df['final_decision'] == 'review').sum()}")
print(f"   🚫 Block:   {(df['final_decision'] == 'block').sum()}")

# Count by risk tier
print("\n📊 By User Risk Tier:")
for tier in ['low', 'medium', 'high']:
    tier_df = df[df['risk_tier'] == tier]
    print(f"   {tier.upper()}: {len(tier_df)} transactions")

# Average ML score by decision
print("\n📊 Average ML Scores:")
print(f"   Approve: {df[df['final_decision'] == 'approve']['ml_score'].mean():.4f}")
print(f"   Review:  {df[df['final_decision'] == 'review']['ml_score'].mean():.4f}")
print(f"   Block:   {df[df['final_decision'] == 'block']['ml_score'].mean():.4f}")

print("\n" + "="*60)
print("✅ Risk Decision Engine completed successfully!")
print("="*60)

# =============================================
# Cleanup
# =============================================

cursor.close()
conn.close()
print("\nDatabase connection closed.")