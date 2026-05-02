from fastapi import APIRouter, Depends, HTTPException
from backend.database import get_db
from backend.auth import hash_password, verify_password, create_access_token
from pydantic import BaseModel



class UserSchema(BaseModel):
    user_name: str
    password: str

router = APIRouter(prefix= "/auth", tags=["Authentication"])

@router.post("/register")
def register(params: UserSchema, db = Depends(get_db)):
    cursor = db.cursor()
    hashed_password = hash_password(params.password)
    try:
        cursor.execute("""
                        INSERT INTO users(user_name, password)
                        VALUES (%s, %s)
                       """, (params.user_name, hashed_password,))
        db.commit()
        return {"message": "User registered successfully."}

    except Exception:
        raise HTTPException(status_code=400, detail="Username already exists.")
    
    finally:
        cursor.close()

@router.post("/login")
def login(params: UserSchema, db = Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("""
                        SELECT password FROM users
                        WHERE user_name = %s
                       """, (params.user_name,))
        row = cursor.fetchone()
    except Exception:
        raise HTTPException(status_code=500, detail="Database Error!")
    finally: 
        cursor.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="User not found!")
    hashed_password = row[0]
    is_correct = verify_password(params.password, hashed_password)
    if is_correct:
        token = create_access_token({"sub": params.user_name})
        return {"access_token": token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="wrong password")
