import sqlite3
from pathlib import Path
import bcrypt
import os

# Get the project root (parent of database directory)
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "ars.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            role TEXT NOT NULL DEFAULT 'staff',  -- 'staff' or 'admin'
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS consignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Consignment Identity
            consignment_no TEXT UNIQUE NOT NULL,
            date TEXT NOT NULL,
            
            -- Consignor Details
            consignor_name TEXT NOT NULL,
            consignor_address TEXT,
            consignor_email TEXT NOT NULL,
            
            -- Consignee Details
            consignee_name TEXT NOT NULL,
            consignee_address TEXT,
            
            -- Route
            from_location TEXT,
            to_location TEXT,
            truck_no TEXT,
            
            -- Goods Description
            description TEXT,
            no_of_packages INTEGER,
            actual_weight TEXT,
            charged_weight TEXT,
            
            -- Invoice Details
            invoice_no TEXT,
            invoice_date TEXT,
            invoice_gst_no TEXT,
            invoice_per TEXT,
            goods_value REAL,
            
            -- Delivery
            delivery_type TEXT DEFAULT 'DD',  -- DD or Door Delivery
            
            -- Insurance
            insurance_by TEXT DEFAULT 'owner',  -- owner or consignor
            insurance_policy_no TEXT,
            insurance_company TEXT,
            insurance_amount REAL,
            
            -- Charges
            freight_rate TEXT,
            freight_amount REAL,
            hamali REAL,
            gst_percent REAL,
            gst_amount REAL,
            st_charge REAL,
            total_amount REAL,
            
            -- E-Way Bill
            eway_bill_no TEXT,
            eway_bill_expiry TEXT,
            
            -- Meta
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pdf_path TEXT,
            email_sent INTEGER DEFAULT 0,
            
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    # Create default admin if not exists
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES ('admin', ?, 'Administrator', 'admin')
        """, (password_hash,))
        print("✅ Default admin created: username=admin, password=admin123")

    conn.commit()
    conn.close()


def get_user_by_username(username: str):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id: int):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
