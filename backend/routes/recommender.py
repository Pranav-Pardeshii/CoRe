from fastapi import APIRouter
from backend.database import get_db

router = APIRouter(prefix="/recommender", tags=["Recommender"])

@router.get("/")
def recommender(percentile: float, category: str, branch: str, division: str):

    division = None if division == "All" else division
    branch = None if branch == "All" else branch
    category = None if category == "All" else category

    db = get_db()
    cursor = db.cursor()
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
    cursor.close()
    db.close()

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