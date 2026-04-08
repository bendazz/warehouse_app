from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
import bcrypt
from models import Inventory, User, engine


class UserCreate(BaseModel):
    username: str
    password: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

app = FastAPI()

@app.get("/inventory")
async def get_inventory():
    with Session(engine) as session:
        statement = select(Inventory)
        items = session.exec(statement).all()
        return items

@app.post("/inventory")
async def create_item(item: Inventory):
    with Session(engine) as session:
        session.add(item)
        session.commit()
        session.refresh(item)
        return item

@app.delete("/inventory/{id}")
async def delete_item(id: int):
    with Session(engine) as session:
        statement = select(Inventory).where(Inventory.id == id)
        record = session.exec(statement).one()
        session.delete(record)
        session.commit()
        return {"deleted": id}

@app.put("/inventory/{id}")
async def update_item(id: int, item: Inventory):
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
        return {"id": new_user.id, "username": new_user.username, "password_hash": new_user.password_hash}

app.mount("/", StaticFiles(directory="static", html=True), name="static")