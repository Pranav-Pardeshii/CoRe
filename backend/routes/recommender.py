from fastapi import APIRouter, Query, Depends, HTTPException
from backend.database import get_db
from pydantic import BaseModel, Field
from typing import Annotated
from backend.auth import get_current_user

router = APIRouter(prefix="/recommender", tags=["Recommender"])

class RecommenderSchema(BaseModel):
    percentile : float = Field(ge = 1, le=100)
    category : str
    branch : str 
    division : str

        

@router.get("/")
def recommender(params: Annotated[RecommenderSchema , Query()], db = Depends(get_db), current_user= Depends(get_current_user)):

    division = None if params.division == "All" else params.division
    branch = None if params.branch == "All" else params.branch
    category = None if params.category == "All" else params.category
    percentile = params.percentile

    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT college_name, branch_name,
                MIN(percentile) as min_cutoff,
                MAX(percentile) as max_cutoff
            FROM cutoffs
            JOIN branches ON cutoffs.branch_code = branches.branch_code
            JOIN colleges ON branches.college_code = colleges.college_code
            WHERE (%s is NULL OR branch_name = %s)
            AND (%s is NULL OR category = %s)
            AND (%s is NULL OR division = %s)
            AND year IN (2024, 2025)
            GROUP BY college_name, branch_name
            HAVING MIN(percentile) <= %s
            ORDER BY max_cutoff DESC
        """, (branch, branch, category, category, division, division, percentile))
        
        result = cursor.fetchall()
        

    except Exception:
        raise HTTPException(status_code=500, detail="Something went wrong, while retrieving data from database")
    
    finally:
        cursor.close()


    colleges = [
        {
            "college": row[0],
            "branch": row[1],
            "min_cutoff": row[2],
            "max_cutoff": row[3],
        }
        for row in result
    ]

    return {"eligible_colleges": colleges, "count": len(colleges)}



if __name__ == '__main__':
    try:
        RecommenderSchema(percentile=150, branch='Computer Engineering', category= 'ST', division= 'Pune')
    except ValueError as e:
        print(e)