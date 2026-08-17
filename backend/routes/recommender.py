from fastapi import APIRouter, Query, Depends, HTTPException
from backend.database import get_db
from pydantic import BaseModel, Field
from typing import Annotated
# from backend.auth import get_current_user

router = APIRouter(prefix="/recommender", tags=["Recommender"])

class RecommenderSchema(BaseModel):
    percentile : float = Field(ge = 1, le=100)
    category : str
    branch : str 
    division : str
    page: int = Field(default=1, ge=1)
    page_size : int = Field(default=10, ge=5, le=30)

        

@router.get("/")
def recommender(params: Annotated[RecommenderSchema , Query()], db = Depends(get_db)):
    # User login is not required for preview

    limit = params.page_size
    offset = (params.page-1)*limit
    division = None if params.division == "All" else params.division
    branch = None if params.branch == "All" else params.branch
    category = None if params.category == "All" else params.category
    percentile = params.percentile

    cursor = db.cursor()

    try:
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT college_name, branch_name, cutoffs.branch_code
                FROM cutoffs
                JOIN branches ON cutoffs.branch_code = branches.branch_code
                JOIN colleges ON branches.college_code = colleges.college_code
                WHERE (%s IS NULL OR branch_name = %s)
                AND (%s IS NULL OR category = %s)
                AND (%s IS NULL OR division = %s)
                AND year IN (2024, 2025)
                AND stage = 'I'
                GROUP BY college_name, branch_name, cutoffs.branch_code
                HAVING MIN(percentile) <= %s
                ) AS counted""",(branch, branch, category, category, division, division, percentile))

        count = cursor.fetchone()

        if count == 0:
            return {"eligible_colleges": "No eligible colleges found for given parameters! Try changing them...", "count": 0}
    
        cursor.execute("""
            SELECT college_name, branch_name, cutoffs.branch_code,
                MIN(percentile) as min_cutoff,
                MAX(percentile) as max_cutoff
            FROM cutoffs
            JOIN branches ON cutoffs.branch_code = branches.branch_code
            JOIN colleges ON branches.college_code = colleges.college_code
            WHERE (%s is NULL OR branch_name = %s)
            AND (%s is NULL OR category = %s)
            AND (%s is NULL OR division = %s)
            AND year IN (2024, 2025)
            AND stage = 'I'
            GROUP BY college_name, branch_name, cutoffs.branch_code
            HAVING MIN(percentile) <= %s
            ORDER BY max_cutoff DESC
            LIMIT %s OFFSET %s
        """, (branch, branch, category, category, division, division, percentile, limit, offset))
        
        result = cursor.fetchall()
        

    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Something went wrong, while retrieving data from database")
    
    finally:
        cursor.close()


    colleges = [
        {
            "college": row[0],
            "branch": row[1],
            "branch_code": row[2],
            "min_cutoff": row[3],
            "max_cutoff": row[4],
        }
        for row in result
    ]

    return {"eligible_colleges": colleges, "count": count}



if __name__ == '__main__':
    try:
        RecommenderSchema(percentile=150, branch='Computer Engineering', category= 'ST', division= 'Pune')
    except ValueError as e:
        print(e)