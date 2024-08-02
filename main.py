import os
from fastapi import FastAPI, HTTPException

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String

from ariadne.asgi import GraphQL
from ariadne import QueryType, MutationType, make_executable_schema

DATABASE_URL = "sqlite:///./test.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

schema_file_path = os.path.join(os.path.dirname(__file__), "schema.graphql")
with open(schema_file_path) as f:
    type_defs = f.read()

query = QueryType()
mutation = MutationType()

@query.field("items")
def resolve_items(_, info):
    db = next(get_db())
    return db.query(Item).all()

@query.field("item")
def resolve_item(_, info, id):
    db = next(get_db())
    return db.query(Item).filter(Item.id == id).first()

@mutation.field("createItem")
def resolve_create_item(_, info, name, description):
    db = next(get_db())
    db_item = Item(name=name, description=description)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@mutation.field("updateItem")
def resolve_update_item(_, info, id, name, description):
    db = next(get_db())
    db_item = db.query(Item).filter(Item.id == id).first()
    if db_item:
        db_item.name = name
        db_item.description = description
        db.commit()
        db.refresh(db_item)
        return db_item
    raise HTTPException(status_code=404, detail="Item not found")

@mutation.field("deleteItem")
def resolve_delete_item(_, info, id):
    db = next(get_db())
    db_item = db.query(Item).filter(Item.id == id).first()
    if db_item:
        db.delete(db_item)
        db.commit()
        return "Item deleted"
    raise HTTPException(status_code=404, detail="Item not found")

schema = make_executable_schema(type_defs, query, mutation)
app = FastAPI()
app.add_route("/graphql", GraphQL(schema, debug=True))
