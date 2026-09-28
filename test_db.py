import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()


conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
)

cursor = conn.cursor()
cursor.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name;
""")


tables = cursor.fetchall()
print("=== 이 DB에 있는 테이블 목록 ===")
for t in tables:
    print(t[0])

cursor.close()
conn.close()

