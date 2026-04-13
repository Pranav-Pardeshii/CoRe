from fastapi import APIRouter
from backend.database import get_db

router = APIRouter()

@router.get('/colleges')
def get_colleges(division: str):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
                    SELECT DISTINCT college_code, college_name
                    FROM colleges 
                    WHERE 
                    division LIKE %s
                   """,(f"%{division}%")
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
