from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException, Depends, Cookie, Response
from pydantic import BaseModel
from sqlmodel import Session, select
import bcrypt
import os
from itsdangerous import URLSafeSerializer
from models import Inventory, User, engine


SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32).hex())
serializer = URLSafeSerializer(SECRET_KEY)
COOKIE_NAME = "session"


class UserCreate(BaseModel):
    username: str
    password: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def get_current_user(session_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME)):
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        user_id = serializer.loads(session_cookie)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")
    with Session(engine) as db:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid session")
        return user


app = FastAPI()

@app.get("/inventory")
async def get_inventory(user: User = Depends(get_current_user)):
    with Session(engine) as session:
        statement = select(Inventory)
        items = session.exec(statement).all()
        return items

@app.post("/inventory")
async def create_item(item: Inventory, user: User = Depends(get_current_user)):
    with Session(engine) as session:
        session.add(item)
        session.commit()
        session.refresh(item)
        return item

@app.delete("/inventory/{id}")
async def delete_item(id: int, user: User = Depends(get_current_user)):
    with Session(engine) as session:
        statement = select(Inventory).where(Inventory.id == id)
        record = session.exec(statement).one()
        session.delete(record)
        session.commit()
        return {"deleted": id}

@app.put("/inventory/{id}")
async def update_item(id: int, item: Inventory, user: User = Depends(get_current_user)):
    with Session(engine) as session:
        statement = select(Inventory).where(Inventory.id == id)
        record = session.exec(statement).one()
        record.name = item.name
        record.category = item.category
        record.brand = item.brand
        record.size = item.size
        record.color = item.color
        record.quantity = item.quantity
        record.price = item.price
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

@app.post("/login")
async def login(user: UserCreate, response: Response):
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == user.username)).first()
        if not existing or not bcrypt.checkpw(user.password.encode(), existing.password_hash.encode()):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        token = serializer.dumps(existing.id)
        response.set_cookie(key=COOKIE_NAME, value=token, httponly=True, samesite="strict")
        return {"id": existing.id, "username": existing.username}

@app.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"message": "Logged out"}

@app.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username}

@app.post("/register")
async def register(user: UserCreate):
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == user.username)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        new_user = User(username=user.username, password_hash=hash_password(user.password))
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return {"id": new_user.id, "username": new_user.username}

app.mount("/", StaticFiles(directory="static", html=True), name="static")