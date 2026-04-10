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
        port= int(os.getenv("DB_PORT")),
        passwd = os.getenv("DB_PASS"),
        database = os.getenv("DB_NAME"),
        use_pure= True,
        )
    return db

@app.get('/')
def home():
    return {'message': 'MHT-CET College predictor'}

@app.get('/recommender')
def recommender(percentile: float, category: str, branch: str, division:str):

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
            SELECT college_name, branch_name,
                   MIN(percentile) as min_cutoff,
                   MAX(percentile) as max_cutoff
            FROM cutoffs
            JOIN branches
            ON cutoffs.branch_code = branches.branch_code
            JOIN colleges
            ON branches.college_code = colleges.college_code
            AND branch_name = %s
            AND category = %s 
            AND division = %s  
            AND year IN(2024, 2025)    
            GROUP BY college_name, branch_name
            HAVING MIN(percentile) <= %s
            ORDER BY max_cutoff DESC
    """, (branch, category,division, percentile)
    )

    result = cursor.fetchall()
    cursor.close()
    db.close()

    colleges =[{
        'college' : row[0],
        'branch' : row[1],
        'min_cutoff' : row[2],
        'max_cutoff' : row[3],
        }
        for row in result
    ]

    return{'Eligible colleges': colleges,
           'count': len(colleges)}


@app.get('/colleges')
def get_colleges(division: str):
    db = get_db()
    cursor = db.cursor()
    division = f"%{division}%"
    cursor.execute("""
                    SELECT DISTINCT college_code, college_name
                    FROM colleges 
                    WHERE 
                    division LIKE %s
                   """,(division,)
                   )
    
    result = cursor.fetchall()
    cursor.close()
    db.close()

    colleges = [
        {
            "college_code" : row[0],
            "college_name" : row[1]
        }
        for row in result
    ]
    return {'Total colleges': colleges,
            'count': len(colleges)}
