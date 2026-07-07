# =============================================
# Fraud Analytics Pipeline
# =============================================

import psycopg2
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_curve, auc, f1_score, classification_report
from xgboost import XGBClassifier
import json

# =============================================
# 1. Extract data from PostgreSQL
# =============================================

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="walley_risk_db",
    user="postgres",
    password="minhduc2004"
)

query = """
SELECT 
    amount,
    transaction_balance_ratio,
    distance_from_home_km,
    user_7day_transaction_count,
    beneficiary_account_age_days,
    time_since_last_login_minutes,
    is_beneficiary_new,
    is_off_hours,
    is_weekend,
    is_new_device,
    is_high_risk_country
FROM transactions;
"""

df = pd.read_sql(query, conn)
conn.close()

print(f"Data extracted: {len(df)} transactions")

# =============================================
# 2. Target definition (Unsupervised anomaly detection)
# =============================================

# Select features for anomaly detection
anomaly_features = ['amount', 'transaction_balance_ratio', 'distance_from_home_km', 
                    'user_7day_transaction_count', 'beneficiary_account_age_days',
                    'time_since_last_login_minutes']

# Fit Isolation Forest
iso_forest = IsolationForest(contamination=0.05, random_state=42)
df['anomaly_score'] = iso_forest.fit_predict(df[anomaly_features])

# Label anomalies as fraud
df['is_fraud'] = (df['anomaly_score'] == -1).astype(int)
print(f"Fraud rate: {df['is_fraud'].mean():.4f} ({df['is_fraud'].sum()} transactions)")

# =============================================
# 3. Feature engineering
# =============================================

# Features for the model (raw, tree-friendly)
features = ['amount', 'transaction_balance_ratio', 'distance_from_home_km',
            'user_7day_transaction_count', 'beneficiary_account_age_days',
            'time_since_last_login_minutes', 
            'is_beneficiary_new', 'is_off_hours', 'is_weekend', 
            'is_new_device', 'is_high_risk_country']

X = df[features]
y = df['is_fraud']

# =============================================
# 4. Stratified train-test split
# =============================================

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Compute scale_pos_weight
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
print(f"Scale Pos Weight: {scale_pos_weight:.2f}")

# =============================================
# 5. Train XGBoost (With imbalance handling)
# =============================================

xgb = XGBClassifier(
    n_estimators=100,
    random_state=42,
    eval_metric='logloss',
    scale_pos_weight=scale_pos_weight
)
xgb.fit(X_train, y_train)

# =============================================
# 6. Evaluation (PR-AUC + Optimal threshold)
# =============================================

# Get predicted probabilities
y_proba = xgb.predict_proba(X_test)[:, 1]

# Calculate PR-AUC
precision, recall, thresholds = precision_recall_curve(y_test, y_proba)
pr_auc = auc(recall, precision)
print(f"PR-AUC: {pr_auc:.4f}")

# Find optimal threshold (maximizing F1)
f1_scores = []
for thresh in thresholds:
    y_pred = (y_proba >= thresh).astype(int)
    f1_scores.append(f1_score(y_test, y_pred))
optimal_threshold = thresholds[f1_scores.index(max(f1_scores))]
print(f"Optimal Threshold: {optimal_threshold:.4f}")

# Classification report at optimal threshold
y_pred_optimal = (y_proba >= optimal_threshold).astype(int)
print("\nClassification Report at Optimal Threshold:")
print(classification_report(y_test, y_pred_optimal))

# =============================================
# 7. Save model & threshold (JSON format)
# =============================================

# Save XGBoost model in JSON format
xgb.save_model('fraud_model.json')
print("Model saved as 'fraud_model.json'")

# Save optimal threshold
with open('optimal_threshold.json', 'w') as f:
    json.dump({'threshold': float(optimal_threshold)}, f)
print("Threshold saved as 'optimal_threshold.json'")