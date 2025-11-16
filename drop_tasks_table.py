import sqlite3
import sys

# --- Configuration ---
DATABASE = 'tasks.db'
TABLE_NAME = 'tasks'

def drop_table(table_name):
    """
    Connects to the database and executes the DROP TABLE command.
    
    :param table_name: The name of the table to drop.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        print(f"Attempting to drop table '{table_name}' from {DATABASE}...")
        
        # Execute the SQL command to delete the table
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        conn.commit()
        print(f"\n✅ Success! Table '{table_name}' has been deleted (dropped) from the database.")
        
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        print(f"\n❌ Error during table deletion: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    # Ensure the Flask server is not running, as it might hold a lock on the database file.
    print("WARNING: Ensure the Flask server (server.py) is STOPPED before running this script.")
    
    # Wait for user confirmation
    input("Press Enter to proceed with deleting the 'tasks' table...")
    
    drop_table(TABLE_NAME)