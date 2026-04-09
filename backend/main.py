from fastapi import FastAPI
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# Initialize database
def get_db():
    db = mysql.connector.connect(
        host = os.getenv("DB_HOST"),
        user = os.getenv("DB_USER"),
        port=int(os.getenv("DB_PORT")),
        passwd = os.getenv("DB_PASS"),
        database = os.getenv("DB_NAME"),
        use_pure= True,
        )
    return db

@app.get('/')
def home():
    return {'message': 'MHT-CET College predictor'}

@app.get('/recommender')
def recommender(percentile: float, category: str, branch: str):

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
            SELECT college_name, branch_name, percentile
            FROM cutoffs
            join branches
            ON cutoffs.branch_code = branches.branch_code
            JOIN colleges
            ON branches.college_code = colleges.college_code
            WHERE percentile <= %s
            AND branch_name = %s
            AND category = %s       
            ORDER BY percentile DESC
    """, (percentile, branch, category)
    )

    result = cursor.fetchall()
    cursor.close()
    db.close()

    colleges =[{
        'college' : row[0],
        'branch' : row[1],
        'percentile' : row[2],
        }
        for row in result
    ]

    return{'Eligible colleges': colleges,
           'count': len(colleges)}

