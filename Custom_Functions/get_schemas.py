import sqlite3

DB_PATH = r"C:\Projects\OpenWebUI\webui.db"

def get_all_schemas():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Print schema for each table
        for table in tables:
            print(f"\nSchema for table '{table}':")
            cursor.execute(f"PRAGMA table_info('{table}');")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[1]} ({col[2]}) {'NOT NULL' if col[3] else ''} {'PRIMARY KEY' if col[5] else ''}")
            
            # Print CREATE TABLE statement
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}';")
            create_stmt = cursor.fetchone()[0]
            print(f"  CREATE TABLE statement: {create_stmt}")
        
        conn.close()
        print("\nAll schemas retrieved successfully.")
    except sqlite3.Error as e:
        print(f"Error retrieving schemas: {e}")

if __name__ == "__main__":
    get_all_schemas()