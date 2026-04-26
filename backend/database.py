import mysql.connector
from dotenv import load_dotenv
import os
from mysql.connector.pooling import MySQLConnectionPool

load_dotenv()

pool = MySQLConnectionPool(
    pool_name='core_pool',
    pool_size=5,
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    port=int(os.getenv("DB_PORT")),
    passwd=os.getenv("DB_PASS"),
    database=os.getenv("DB_NAME"),
    ssl_ca=os.getenv("DB_SSL_CA"),
    use_pure=True,
)

def get_db():
    db = pool.get_connection()
    try:
        yield db
    finally:
        db.close()

