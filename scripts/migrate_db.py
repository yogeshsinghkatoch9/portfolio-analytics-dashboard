import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from backend import db
from backend import db
from sqlalchemy import text as sql_text

def run_migration():
    print("Running migration...")
    try:
        with db.engine.connect() as conn:
            # Check for asset_type
            print("Checking holdings table...")
            result = conn.execute(sql_text("PRAGMA table_info(holdings)"))
            columns = [row[1] for row in result.fetchall()]
            print(f"Current columns: {columns}")
            
            if 'asset_type' not in columns:
                print("Adding asset_type column...")
                conn.execute(sql_text("ALTER TABLE holdings ADD COLUMN asset_type VARCHAR DEFAULT 'Stock'"))
            else:
                print("asset_type already exists.")
                
            if 'currency' not in columns:
                print("Adding currency column...")
                conn.execute(sql_text("ALTER TABLE holdings ADD COLUMN currency VARCHAR DEFAULT 'USD'"))
            else:
                print("currency already exists.")
                
            # Check for Watchlist tables
            # SQLite doesn't have "CREATE TABLE IF NOT EXISTS" for complex relaionships easily via raw SQL 
            # without full schema, but we can check if table exists
            print("Checking watchlists and watchlist_items tables...")
            tables = conn.execute(sql_text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
            table_names = [t[0] for t in tables]
            
            if 'watchlists' not in table_names:
                print("Creating watchlists table...")
                conn.execute(sql_text("""
                    CREATE TABLE watchlists (
                        id INTEGER PRIMARY KEY,
                        name VARCHAR DEFAULT 'My Watchlist'
                    )
                """))
            else:
                print("watchlists table already exists.")
                
            if 'watchlist_items' not in table_names:
                print("Creating watchlist_items table...")
                conn.execute(sql_text("""
                    CREATE TABLE watchlist_items (
                        id INTEGER PRIMARY KEY,
                        watchlist_id INTEGER NOT NULL,
                        ticker VARCHAR,
                        added_at DATETIME,
                        FOREIGN KEY(watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE
                    )
                """))
                conn.execute(sql_text("CREATE INDEX ix_watchlist_items_ticker ON watchlist_items (ticker)"))
            else:
                print("watchlist_items table already exists.")
                
            conn.commit()
            print("Migration complete.")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
