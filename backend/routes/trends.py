from fastapi import APIRouter, Query, Depends, HTTPException
from backend.database import get_db
from pydantic import BaseModel, Field
from typing import Annotated

router = APIRouter(prefix="/trends", tags=["Trends"] )

class TrendsSchema(BaseModel):
    branch_code : int
    category : str

@router.get("/")
def trends(params: Annotated[TrendsSchema, Query()], db = Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT year, round, percentile
            FROM cutoffs
            WHERE cutoffs.branch_code = %s
                AND category = %s
            ORDER BY year, round
            """, (params.branch_code, params.category))
        
        result = cursor.fetchall()

    except Exception:
        raise HTTPException(status_code=500, detail="Something went wrong, while retrieving data from database")

    finally:
        cursor.close()

    trends_list = []
    for row in result:
        trends_list.append({
            'year': row[1],
            'round': row[2],
            'percentile': row[3]
        })

    return {'branch_code': params.branch_code, 
            'count': len(trends_list),
            'trends':trends_list}