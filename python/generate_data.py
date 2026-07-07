import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import uuid

# =============================================
# Configuration
# =============================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "walley_risk_db",
    "user": "postgres",
    "password": "minhduc2004"  # REPLACE WITH YOUR ACTUAL PASSWORD
}

NUM_USERS = 1000
NUM_BENEFICIARIES = 500
NUM_TRANSACTIONS = 10000
NUM_AUTHS = 5000

VIETNAMESE_FIRST_NAMES = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Vu", "Dang", "Bui", "Do", "Ho"]
VIETNAMESE_LAST_NAMES = ["Van", "Thi", "Huu", "Quang", "Minh", "Thanh", "Anh", "Trong", "Xuan", "Hong"]
VIETNAMESE_CITIES = ["Ho Chi Minh City", "Hanoi", "Da Nang", "Can Tho", "Hai Phong", "Bien Hoa", "Nha Trang", "Hue", "Vung Tau", "Quy Nhon"]
HIGH_RISK_COUNTRIES = ["North Korea", "Iran", "Syria", "Myanmar", "Russia", "Belarus", "Venezuela"]

# =============================================
# Helper functions
# =============================================

phone_counter = 0

def generate_phone():
    """Generate a Vietnamese phone number with intentional dirty formats, ensuring uniqueness."""
    global phone_counter
    phone_counter += 1
    base_number = f"0{random.randint(3, 9)}{random.randint(10000000, 99999999)}"
    # Use counter to ensure uniqueness while maintaining dirty formats
    if random.random() < 0.15:
        return f"+84{base_number[1:]}"
    elif random.random() < 0.15:
        return f"84{base_number[1:]}"
    else:
        return base_number

def generate_name():
    """Generate a Vietnamese full name."""
    return f"{random.choice(VIETNAMESE_FIRST_NAMES)} {random.choice(VIETNAMESE_LAST_NAMES)}"

email_counter = 0

def generate_email(name):
    """Generate a unique email from a name."""
    global email_counter
    email_counter += 1
    domains = ["gmail.com", "yahoo.com", "outlook.com", "email.com"]
    clean_name = name.lower().replace(" ", ".")
    return f"{clean_name}{email_counter}@{random.choice(domains)}"

def random_date(start, end):
    """Generate a random datetime between start and end."""
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + timedelta(seconds=random_second)

def random_bool(weight_true=0.5):
    """Generate a random boolean with given weight."""
    return random.random() < weight_true

# =============================================
# Generate data
# =============================================

def generate_users():
    """Generate NUM_USERS realistic user records with intentional dirty data."""
    users = []
    for _ in range(NUM_USERS):
        name = generate_name()
        city = random.choice(VIETNAMESE_CITIES)
        is_active = random_bool(0.92)
        kyc_status = random.choices(
            ["pending", "verified", "rejected", "expired"],
            weights=[0.1, 0.75, 0.05, 0.1]
        )[0]
        risk_tier = random.choices(
            ["low", "medium", "high"],
            weights=[0.7, 0.2, 0.1]
        )[0]
        last_login = random_date(
            datetime.now() - timedelta(days=90),
            datetime.now()
        )
        created_at = random_date(
            datetime.now() - timedelta(days=365),
            datetime.now()
        )
        # Some users have negative balance (dirty)
        balance = round(random.uniform(-50000, 100000000), 2) if random.random() < 0.01 else round(random.uniform(0, 50000000), 2)
        # Some users have missing city
        if random.random() < 0.02:
            city = None
        users.append({
            "user_id": str(uuid.uuid4()),
            "full_name": name,
            "email": generate_email(name),
            "phone": generate_phone(),
            "wallet_balance": balance,
            "home_city": city,
            "home_country": "Vietnam",
            "created_at": created_at,
            "kyc_status": kyc_status,
            "risk_tier": risk_tier,
            "is_active": is_active,
            "last_login_timestamp": last_login
        })
    return users

def generate_beneficiaries(users):
    """Generate NUM_BENEFICIARIES beneficiary records."""
    beneficiaries = []
    for _ in range(NUM_BENEFICIARIES):
        name = generate_name()
        country = random.choices(
            ["Vietnam", "Singapore", "Malaysia", "Thailand", "Japan", "South Korea", "USA", "UK", "Australia"] + HIGH_RISK_COUNTRIES,
            weights=[0.65] + [0.03]*8 + [0.02]*7
        )[0]
        created_at = random_date(
            datetime.now() - timedelta(days=180),
            datetime.now()
        )
        beneficiaries.append({
            "beneficiary_id": str(uuid.uuid4()),
            "beneficiary_name": name,
            "beneficiary_phone": generate_phone() if random.random() > 0.05 else None,
            "beneficiary_bank_account": f"{random.randint(100000, 999999)}{random.randint(100000, 999999)}" if random.random() > 0.1 else None,
            "beneficiary_country": country,
            "created_at": created_at,
            "is_verified": random_bool(0.6),
            "total_transactions_received": 0,
            "unique_senders_count": 0,
            "first_transaction_date": None,
            "last_transaction_date": None
        })
    return beneficiaries

def generate_transactions(users, beneficiaries):
    """Generate NUM_TRANSACTIONS transaction records with dirty data."""
    transactions = []
    for i in range(NUM_TRANSACTIONS):
        user = random.choice(users)
        beneficiary = random.choice(beneficiaries)
        # Intentionally make beneficiary_id invalid (dirty)
        if random.random() < 0.01:
            beneficiary = {"beneficiary_id": str(uuid.uuid4())}
        
        amount = round(random.uniform(1000, 50000000), 2)
        # Some amounts are negative (dirty)
        if random.random() < 0.005:
            amount = round(random.uniform(-500000, -1000), 2)
        # Some amounts are huge (dirty)
        if random.random() < 0.005:
            amount = round(random.uniform(100000000, 1000000000), 2)
        
        txn_time = random_date(
            datetime.now() - timedelta(days=30),
            datetime.now()
        )
        # Some transactions happen before login (dirty)
        last_login = user["last_login_timestamp"] if random.random() > 0.1 else None
        if last_login and random.random() < 0.03:
            txn_time = last_login - timedelta(minutes=random.randint(1, 60))
        
        # Dirty: Some transactions have missing timestamp
        if random.random() < 0.02:
            txn_time = None
        
        status = random.choices(
            ["pending", "approved", "blocked", "review"],
            weights=[0.05, 0.8, 0.05, 0.1]
        )[0]
        final_decision = random.choices(
            ["pending", "approve", "review", "block"],
            weights=[0.05, 0.8, 0.1, 0.05]
        )[0]
        rule_flags = []
        if random.random() < 0.1:
            rule_flags.append("velocity_rule")
        if random.random() < 0.08:
            rule_flags.append("new_beneficiary_rule")
        if beneficiary.get("beneficiary_country") in HIGH_RISK_COUNTRIES and random.random() < 0.3:
            rule_flags.append("high_risk_country_rule")
        
        # Derived features with dirty injection
        ratio = round(random.uniform(0, 0.99), 4)
        if random.random() < 0.02:
            ratio = None  # Missing ratio
        
        is_new_device = random_bool(0.15)
        
        # Handle None timestamp for derived features
        if txn_time is not None:
            is_off_hours = txn_time.hour < 6 or txn_time.hour > 22
            is_weekend = txn_time.weekday() in [5, 6]
        else:
            is_off_hours = False
            is_weekend = False
        
        # Duplicate injection
        if random.random() < 0.01 and transactions:
            duplicate_txn = transactions[-1].copy()
            if duplicate_txn:
                duplicate_txn["transaction_id"] = str(uuid.uuid4())
                duplicate_txn["timestamp"] = txn_time + timedelta(seconds=random.randint(1, 10)) if txn_time else None
                duplicate_txn["rule_flags"] = rule_flags
                duplicate_txn["is_beneficiary_new"] = random_bool(0.3)
                duplicate_txn["is_new_device"] = random_bool(0.15)
                transactions.append(duplicate_txn)
        
        is_beneficiary_new = random_bool(0.3)
        beneficiary_age_days = random.randint(0, 180) if is_beneficiary_new else random.randint(30, 180)
        if random.random() < 0.03:
            beneficiary_age_days = -5  # Dirty
        
        # Handle None timestamp for reviewed_at
        if random.random() < 0.1:
            if txn_time is not None:
                reviewed_at = txn_time + timedelta(hours=random.randint(1, 48))
            else:
                reviewed_at = None
        else:
            reviewed_at = None
        
        transactions.append({
            "transaction_id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "beneficiary_id": beneficiary["beneficiary_id"],
            "amount": amount,
            "timestamp": txn_time,
            "status": status,
            "fraud_score": round(random.uniform(0, 1), 4) if random.random() > 0.05 else None,
            "final_decision": final_decision,
            "reviewed_by": f"investigator_{random.randint(1, 20)}" if random.random() < 0.1 else None,
            "reviewed_at": reviewed_at,
            "rule_flags": rule_flags,
            "transaction_balance_ratio": ratio,
            "is_beneficiary_new": is_beneficiary_new,
            "is_off_hours": is_off_hours,
            "is_weekend": is_weekend,
            "distance_from_home_km": round(random.uniform(0, 5000), 2) if random.random() > 0.01 else -5.0,
            "user_7day_transaction_count": random.randint(0, 50),
            "is_new_device": is_new_device,
            "beneficiary_account_age_days": beneficiary_age_days,
            "time_since_last_login_minutes": random.randint(1, 60) if random.random() > 0.1 else None,
            "is_high_risk_country": beneficiary.get("beneficiary_country") in HIGH_RISK_COUNTRIES
        })
    return transactions

def generate_device_auths(users):
    """Generate NUM_AUTHS device authentication records."""
    auths = []
    for _ in range(NUM_AUTHS):
        user = random.choice(users)
        login_time = random_date(
            datetime.now() - timedelta(days=30),
            datetime.now()
        )
        is_suspicious = random_bool(0.05)
        is_proxy_vpn = random_bool(0.05) or is_suspicious
        is_emulator = random_bool(0.02) or is_suspicious
        country = random.choices(
            ["Vietnam", "Singapore", "USA", "UK", "Japan", "China", "Russia", "North Korea"],
            weights=[0.7, 0.05, 0.05, 0.05, 0.03, 0.03, 0.02, 0.02]
        )[0]
        # Some dirty: login after transaction time (impossible)
        if random.random() < 0.01 and user["last_login_timestamp"]:
            login_time = user["last_login_timestamp"] + timedelta(seconds=random.randint(1, 60))
        auths.append({
            "auth_id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "device_id": f"device_{uuid.uuid4().hex[:16]}",
            "login_timestamp": login_time,
            "ip_geolocation_country": country,
            "ip_geolocation_city": random.choice(VIETNAMESE_CITIES),
            "is_proxy_vpn": is_proxy_vpn,
            "is_emulator": is_emulator,
            "is_suspicious_login": is_suspicious,
            "os_type": random.choice(["iOS", "Android", "Windows", "Mac", "Linux"]),
            "browser_fingerprint": f"browser_{uuid.uuid4().hex[:16]}",
            "session_duration_minutes": random.randint(1, 180) if random.random() > 0.1 else None
        })
    return auths

# =============================================
# Insert data into PostgreSQL
# =============================================

def insert_data(conn, users, beneficiaries, transactions, auths):
    """Insert all generated data into the database."""
    cur = conn.cursor()
    
    # Insert users
    print("Inserting users...")
    for user in users:
        cur.execute("""
            INSERT INTO users (
                user_id, full_name, email, phone, wallet_balance,
                home_city, home_country, created_at, kyc_status,
                risk_tier, is_active, last_login_timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user["user_id"], user["full_name"], user["email"], user["phone"],
            user["wallet_balance"], user["home_city"], user["home_country"],
            user["created_at"], user["kyc_status"], user["risk_tier"],
            user["is_active"], user["last_login_timestamp"]
        ))
    
    # Insert beneficiaries
    print("Inserting beneficiaries...")
    for ben in beneficiaries:
        cur.execute("""
            INSERT INTO beneficiaries (
                beneficiary_id, beneficiary_name, beneficiary_phone,
                beneficiary_bank_account, beneficiary_country,
                created_at, is_verified, total_transactions_received,
                unique_senders_count, first_transaction_date, last_transaction_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            ben["beneficiary_id"], ben["beneficiary_name"], ben["beneficiary_phone"],
            ben["beneficiary_bank_account"], ben["beneficiary_country"],
            ben["created_at"], ben["is_verified"], ben["total_transactions_received"],
            ben["unique_senders_count"], ben["first_transaction_date"], ben["last_transaction_date"]
        ))
    
    # Insert transactions
    print("Inserting transactions...")
    for txn in transactions:
        cur.execute("""
            INSERT INTO transactions (
                transaction_id, user_id, beneficiary_id, amount, timestamp,
                status, fraud_score, final_decision, reviewed_by,
                reviewed_at, rule_flags, transaction_balance_ratio,
                is_beneficiary_new, is_off_hours, is_weekend,
                distance_from_home_km, user_7day_transaction_count,
                is_new_device, beneficiary_account_age_days,
                time_since_last_login_minutes, is_high_risk_country
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            txn["transaction_id"], txn["user_id"], txn["beneficiary_id"],
            txn["amount"], txn["timestamp"], txn["status"],
            txn["fraud_score"], txn["final_decision"], txn["reviewed_by"],
            txn["reviewed_at"], txn["rule_flags"],
            txn["transaction_balance_ratio"], txn["is_beneficiary_new"],
            txn["is_off_hours"], txn["is_weekend"],
            txn["distance_from_home_km"], txn["user_7day_transaction_count"],
            txn["is_new_device"], txn["beneficiary_account_age_days"],
            txn["time_since_last_login_minutes"], txn["is_high_risk_country"]
        ))
    
    # Insert device authentications
    print("Inserting device authentications...")
    for auth in auths:
        cur.execute("""
            INSERT INTO device_authentications (
                auth_id, user_id, device_id, login_timestamp,
                ip_geolocation_country, ip_geolocation_city,
                is_proxy_vpn, is_emulator, is_suspicious_login,
                os_type, browser_fingerprint, session_duration_minutes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            auth["auth_id"], auth["user_id"], auth["device_id"],
            auth["login_timestamp"], auth["ip_geolocation_country"],
            auth["ip_geolocation_city"], auth["is_proxy_vpn"],
            auth["is_emulator"], auth["is_suspicious_login"],
            auth["os_type"], auth["browser_fingerprint"],
            auth["session_duration_minutes"]
        ))
    
    conn.commit()
    cur.close()
    print("All data inserted successfully!")

# =============================================
# Main execution
# =============================================

def main():
    print("Generating data...")
    users = generate_users()
    beneficiaries = generate_beneficiaries(users)
    transactions = generate_transactions(users, beneficiaries)
    auths = generate_device_auths(users)
    
    print(f"Generated {len(users)} users")
    print(f"Generated {len(beneficiaries)} beneficiaries")
    print(f"Generated {len(transactions)} transactions")
    print(f"Generated {len(auths)} device authentications")
    
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        insert_data(conn, users, beneficiaries, transactions, auths)
        conn.close()
        print("Data generation complete!")
    except Exception as e:
        print(f"Error: {e}")
        print("Please check your database credentials and ensure PostgreSQL is running.")

if __name__ == "__main__":
    main()