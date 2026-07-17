from fastapi import APIRouter, Query, Depends, HTTPException
from backend.database import get_db
from pydantic import BaseModel, Field
from typing import Annotated

router = APIRouter(prefix="/trends", tags=["Trends"] )

class TrendsSchema(BaseModel):
    branch_code : str
    category : str 

@router.get("/")
def trends(params: Annotated[TrendsSchema, Query()], db = Depends(get_db)):
    category = None if params.category == 'All' else params.category
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT year, round, percentile
            FROM cutoffs
            WHERE cutoffs.branch_code = %s
                AND (%s is NULL OR category = %s)
                AND stage = 'I'
            ORDER BY year, round
            """, (params.branch_code, category, category))
        
        result = cursor.fetchall()

    except Exception:
        raise HTTPException(status_code=500, detail="Something went wrong, while retrieving data from database")

    finally:
        cursor.close()

    trends_list = []
    for row in result:
        trends_list.append({
            'year': row[0],
            'round': row[1],
            'percentile': row[2]
        })

    return {'branch_code': params.branch_code, 
            'count': len(trends_list),
            'trends':trends_list}