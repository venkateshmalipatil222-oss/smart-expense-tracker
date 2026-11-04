import sqlite3
import os

db_path = os.path.join("data", "expense_tracker.db")

def migrate():
    if not os.path.exists(db_path):
        print("Database not found, skipping migration.")
        return

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cols = [col[1] for col in cur.execute("PRAGMA table_info(transactions)").fetchall()]

    if "currency" not in cols:
        print("Adding currency column...")
        cur.execute("ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD' NOT NULL")

    if "exchange_rate" not in cols:
        print("Adding exchange_rate column...")
        cur.execute("ALTER TABLE transactions ADD COLUMN exchange_rate FLOAT DEFAULT 1.0 NOT NULL")

    if "original_amount" not in cols:
        print("Adding original_amount column...")
        cur.execute("ALTER TABLE transactions ADD COLUMN original_amount FLOAT")

    cur.execute("UPDATE transactions SET currency = 'USD', exchange_rate = 1.0, original_amount = amount WHERE original_amount IS NULL")
    con.commit()
    
    updated_cols = [col[1] for col in cur.execute("PRAGMA table_info(transactions)").fetchall()]
    print("Database schema up to date. Columns:", updated_cols)
    con.close()

if __name__ == "__main__":
    migrate()

