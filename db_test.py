import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

def test_db_connection():
    try:
        connection = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'pharmacy'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        print("Connected successfully to MySQL")
        connection.close()
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")

if __name__ == "__main__":
    test_db_connection()
