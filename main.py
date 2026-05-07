# import os
# from fastapi import FastAPI
# from google.cloud.sql.connector import Connector
# from sqlalchemy import create_engine, text
# from sqlalchemy.orm import sessionmaker

# app = FastAPI()

# # 1. Environment Variables (Set these in Cloud Run)
# INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME") # project:region:instance
# DB_USER = os.environ.get("DB_USER")
# DB_PASS = os.environ.get("DB_PASS")
# DB_NAME = os.environ.get("DB_NAME")

# # 2. Initialize Cloud SQL Connector
# connector = Connector()

# def getconn():
#     conn = connector.connect(
#         INSTANCE_CONNECTION_NAME,
#         "pg8000",
#         user=DB_USER,
#         password=DB_PASS,
#         db=DB_NAME
#     )
#     return conn

# # 3. Create SQLAlchemy Engine with Connection Pool
# engine = create_engine(
#     "postgresql+pg8000://",
#     creator=getconn,
# )

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# @app.get("/")
# def read_root():
#     return {"status": "Cloud Run is active"}

# @app.get("/db-test")
# def test_db_connection():
#     try:
#         with engine.connect() as conn:
#             # Simple query to verify connection
#             result = conn.execute(text("SELECT current_database(), now();"))
#             row = result.fetchone()
#             return {
#                 "database": row[0],
#                 "server_time": str(row[1]),
#                 "connection": "Successful"
#             }
#     except Exception as e:
#         return {"error": str(e), "connection": "Failed"}

# # Cleanup connector on shutdown
# @app.on_event("shutdown")
# def shutdown_event():
#     connector.close()


import os
from typing import List
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from google.cloud.sql.connector import Connector
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Serve index.html at the root URL
@app.get("/")
async def serve_index():
    return FileResponse('index.html')


# --- CONFIGURATION ---
INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
DB_NAME = os.environ.get("DB_NAME")

Base = declarative_base()

# --- MODELS ---
class City(Base):
    __tablename__ = "cities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    vote_count = Column(Integer, default=0)

class Vote(Base):
    __tablename__ = "votes"
    id = Column(Integer, primary_key=True, index=True)
    voter_email = Column(String, nullable=False)
    city_id = Column(Integer, ForeignKey("cities.id"))

# --- DATABASE CONNECTION ---
connector = Connector()

def getconn():
    return connector.connect(
        INSTANCE_CONNECTION_NAME, "pg8000",
        user=DB_USER, password=DB_PASS, db=DB_NAME
    )

engine = create_engine("postgresql+pg8000://", creator=getconn)
SessionLocal = sessionmaker(bind=engine)

# --- SCHEMAS ---
class VoteRequest(BaseModel):
    voter_email: str
    # User must pick exactly 3 unique cities
    city_ids: List[int] = Field(..., min_items=3, max_items=3)

# --- APP SETUP ---
app = FastAPI(title="India Top 3 Cities Voting API")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    # Seed the 5 candidate cities
    with SessionLocal() as db:
        if db.query(City).count() == 0:
            cities = [City(name=n) for n in ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai"]]
            db.add_all(cities)
            db.commit()

# --- ROUTES ---

@app.get("/cities")
def list_cities(db: Session = Depends(lambda: SessionLocal())):
    return db.query(City).all()

@app.post("/vote")
def cast_vote(request: VoteRequest, db: Session = Depends(lambda: SessionLocal())):
    # 1. Check for duplicates in the request
    if len(set(request.city_ids)) < 3:
        raise HTTPException(status_code=400, detail="Please pick 3 unique cities.")

    # 2. Check if user already voted (Simple email check)
    existing_vote = db.query(Vote).filter(Vote.voter_email == request.voter_email).first()
    if existing_vote:
        raise HTTPException(status_code=403, detail="You have already cast your votes.")

    # 3. Validate city IDs exist and record votes
    cities = db.query(City).filter(City.id.in_(request.city_ids)).all()
    if len(cities) != 3:
        raise HTTPException(status_code=404, detail="One or more selected cities not found.")

    for city in cities:
        city.vote_count += 1
        db.add(Vote(voter_email=request.voter_email, city_id=city.id))
    
    db.commit()
    return {"message": "Votes cast successfully!", "your_picks": [c.name for c in cities]}

@app.get("/results")
def get_results(db: Session = Depends(lambda: SessionLocal())):
    # Return cities ordered by highest votes
    return db.query(City).order_by(City.vote_count.desc()).all()

@app.on_event("shutdown")
def shutdown():
    connector.close()

