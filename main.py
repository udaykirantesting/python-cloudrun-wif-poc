import os
from fastapi import FastAPI
from google.cloud.sql.connector import Connector
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

app = FastAPI()

# 1. Environment Variables (Set these in Cloud Run)
INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME") # project:region:instance
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
DB_NAME = os.environ.get("DB_NAME")

# 2. Initialize Cloud SQL Connector
connector = Connector()

def getconn():
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pg8000",
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME
    )
    return conn

# 3. Create SQLAlchemy Engine with Connection Pool
engine = create_engine(
    "postgresql+pg8000://",
    creator=getconn,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@app.get("/")
def read_root():
    return {"status": "Cloud Run is active"}

@app.get("/db-test")
def test_db_connection():
    try:
        with engine.connect() as conn:
            # Simple query to verify connection
            result = conn.execute(text("SELECT current_database(), now();"))
            row = result.fetchone()
            return {
                "database": row[0],
                "server_time": str(row[1]),
                "connection": "Successful"
            }
    except Exception as e:
        return {"error": str(e), "connection": "Failed"}

# Cleanup connector on shutdown
@app.on_event("shutdown")
def shutdown_event():
    connector.close()
