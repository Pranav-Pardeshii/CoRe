from fastapi import FastAPI
from backend.routes import recommender, auth


app = FastAPI(title="CoRe - MHT-CET College Predictor")

app.include_router(recommender.router)
app.include_router(auth.router)

@app.get("/")
def home():
    return {"message": "MHT-CET College Predictor"}