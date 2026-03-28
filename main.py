from fastapi import FastAPI
import mysql.connector

app = FastAPI()

# Initialize database
def get_db():
    db = mysql.connector.connect(
        host = 'localhost',
        user = 'root',
        passwd = 'root',
        use_pure= True,
        database = 'admission'
        )
    return db

@app.get('/')
def home():
    return {'message': 'MHT-CET College predictor'}

@app.get('/recommender')
def recommender(percentile: float, caste: str, branch: str):

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
            SELECT college_name, branch_name, cutoff_percentile
            FROM cutoffs
            join colleges
            ON colleges.college_id = cutoffs.college_id
            JOIN branches
            ON cutoffs.branch_id = branches.branch_id
            WHERE cutoff_percentile <= %s
            AND branch_name = %s
            AND category = %s       
            ORDER BY cutoff_percentile DESC
    """, (percentile, branch, caste)
    )

    result = cursor.fetchall()
    cursor.close()
    db.close()

    colleges =[{
        'college' : row[0],
        'branch' : row[1],
        'cutoff_percentile' : row[2],
        }
        for row in result
    ]

    return{'Eligible colleges': colleges,
           'count': len(colleges)}

