from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from backend.database import get_db
from backend.auth import get_current_user
import mysql.connector.errors as me

router = APIRouter(prefix='/saved-lists', tags=['Saved List'])

class SavedListSchema(BaseModel):
    branch_code: str

class ReorderSchema(BaseModel):
    ordered_list: list[int]

# Add an Item to the list
@router.post("/")
def create_item(params: SavedListSchema, db = Depends(get_db), current_user = Depends(get_current_user)):
    cursor = db.cursor()
    try:
        # Get college_name and branch_name from college_code to store them denormalized into saved_list
        cursor.execute("""
                       SELECT colleges.college_code, college_name, branch_name 
                       FROM branches
                       INNER JOIN colleges
                            ON branches.college_code = colleges.college_code
                       WHERE branch_code = %s
                       """, (params.branch_code,))
        
        result = cursor.fetchone()
        if result:
            college_code, college_name, branch_name = result
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
                       """, (current_user , college_code, params.branch_code, college_name, branch_name, rank)) 
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

# Delete an Item from the list
@router.delete("/{id}")
def delete_item(id: int, db = Depends(get_db), current_user = Depends(get_current_user)):
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM saved_list WHERE id = %s AND user_id = %s", (id, int(current_user)))
        db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found!")
        return {"message":"Item deleted successfully!"}
    
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="An unexpected error occured!")
    finally:
        cursor.close()

# Update the database for the new rank
@router.put("/")
def reorder(params: ReorderSchema, db = Depends(get_db), current_user = Depends(get_current_user)):
    cursor = db.cursor()
    try:
        # Validate every id in the request actually belongs to this user, up front
        cursor.execute("SELECT id FROM saved_list WHERE user_id = %s", (int(current_user),))
        owned_ids = {row[0] for row in cursor.fetchall()}

        if set(params.ordered_list) != owned_ids:
            raise HTTPException(status_code=400, detail="Invalid Input!")

        for index, id in enumerate(params.ordered_list):
            new_rank = index + 1
            cursor.execute("UPDATE saved_list SET `rank` = %s WHERE id = %s AND user_id = %s", (new_rank, id, int(current_user)))
            # no rowcount check here anymore — ownership already verified above

        db.commit()
        return {"message": "Bingo! list reordered successfully!"}

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="An unexpected error occured while updating the list! Please retry...")
    finally:
        cursor.close()

# Get the saved_list 
@router.get("/")
def get_saved_list(db = Depends(get_db), current_user = Depends(get_current_user)):
    cursor = db.cursor()
    try:
        cursor.execute("SELECT id, college_name, branch_name FROM saved_list WHERE user_id = %s ORDER BY `rank` ASC", (int(current_user),))
        if cursor.rowcount == 0:
            return {"saved_list":[]}
        result = cursor.fetchall()
        saved_colleges = [
            {
                'id' : row[0],
                'college_name' : row[1],
                'branch_name' : row[2]
            }
            for row in result
        ]

        return {"saved_list":saved_colleges}

    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="An unexpected error occured!")
    finally:
        cursor.close()