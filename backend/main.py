from fastapi import FastAPI, Depends
from backend.routes import recommender, auth
from backend.database import get_db


app = FastAPI(title="CoRe - MHT-CET College Predictor")

app.include_router(recommender.router)
app.include_router(auth.router)

@app.get("/")
def home():
    return {"message": "MHT-CET College Predictor"}

@app.get("/ping")
def ping(db = Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("SELECT 1;")
        cursor.fetchall()
    return {"status": "Aiven MySQL Database is awake!"}