import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def create_database():
    host = os.getenv('DB_HOST', 'localhost')
    user = os.getenv('DB_USER', 'root')
    password = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'pharmacy')
    port = int(os.getenv('DB_PORT', 3306))

    print(f"Connecting to MySQL at {host}:{port} as {user}...")
    
    try:
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=port
        )
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"Database '{db_name}' verified/created successfully.")
        
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Error creating database: {e}")

if __name__ == "__main__":
    create_database()
