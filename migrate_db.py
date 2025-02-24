from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlite3

# Create a new engine that connects to the database
engine = create_engine("sqlite:///./exercises.db")

def migrate_db():
    # Connect directly with sqlite3 to alter the table
    conn = sqlite3.connect('./exercises.db')
    cursor = conn.cursor()
    
    try:
        # Add the new column
        cursor.execute('''
        ALTER TABLE exercises 
        ADD COLUMN image_url VARCHAR(1024)
        ''')
        conn.commit()
        print("Successfully added image_url column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column image_url already exists")
        else:
            print(f"Error adding column: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db() 