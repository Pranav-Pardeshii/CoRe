import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        port=int(os.getenv("DB_PORT")),
        passwd=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        ssl_ca=os.getenv("DB_SSL_CA"),
        use_pure=True,
    )