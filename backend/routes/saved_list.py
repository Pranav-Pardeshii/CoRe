from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.database import get_db
from backend.auth import get_current_user
import mysql.connector.errors as me

router = APIRouter(prefix='/saved-lists', tags=['Saved List'])

class SavedListSchema(BaseModel):
    branch_code: str
    college_code: str

#Add an Item to the list
@router.post("/")
def saved_list(params: SavedListSchema, db = Depends(get_db), current_user = Depends(get_current_user)):
    cursor = db.cursor()
    try:
        #Get college_name and branch_name from college_code to store them denormalized into saved_list
        cursor.execute("""
                       SELECT college_name, branch_name 
                       FROM colleges
                       INNER JOIN branches
                            ON branches.college_code = colleges.college_code
                       WHERE colleges.college_code = %s
                            AND branch_code = %s
                       """, (params.college_code, params.branch_code))
        
        result = cursor.fetchone()
        if result:
            college_name, branch_name = result
        else:
            raise HTTPException(status_code=400, detail="Invalid college_code or branch_code!")
  
        #Get Current max Rank
        #To assign the rank value to the new entry
        cursor.execute("SELECT MAX(`rank`) from saved_list WHERE user_id = %s",(current_user,))
        result = cursor.fetchone()[0]
        rank = 1 if result is None else result + 1

        #Insert the data into the table
        cursor.execute("""
                       INSERT INTO saved_list (user_id, college_code, branch_code, college_name, branch_name, `rank`)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       """, (current_user , params.college_code, params.branch_code, college_name, branch_name, rank)) 
        db.commit()
        return{"message":"Item saved successfully."}
    
    except HTTPException:
        db.rollback()
        raise

    except me.IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="You already saved this Item")
    
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="An unexpected error occured!")
    
    finally:
        cursor.close()

# # Delete an Item from the list
# @router.delete("/")
# def delete_saved_branch()
