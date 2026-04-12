from fastapi import FastAPI
from routes import recommender

app = FastAPI(title="CoRe - MHT-CET College Predictor")

app.include_router(recommender.router)

@app.get("/")
def home():
    return {"message": "MHT-CET College Predictor"}