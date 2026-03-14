import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from motor.motor_asyncio import AsyncIOMotorClient

# PostgreSQL Connection URLs
PRIMARY_URL = os.getenv("DATABASE_URL_PRIMARY", "postgresql://postgres:postgres@localhost:5432/saas_db")
REPLICA_1_URL = os.getenv("DATABASE_URL_REPLICA_1", "postgresql://postgres:postgres@localhost:5433/saas_db")
REPLICA_2_URL = os.getenv("DATABASE_URL_REPLICA_2", "postgresql://postgres:postgres@localhost:5434/saas_db")

# Engines
writer_engine = create_engine(PRIMARY_URL, pool_pre_ping=True)
reader_engine_1 = create_engine(REPLICA_1_URL, pool_pre_ping=True)
reader_engine_2 = create_engine(REPLICA_2_URL, pool_pre_ping=True)

# Session Locals
WriterSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=writer_engine)
Reader1SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=reader_engine_1)
Reader2SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=reader_engine_2)

Base = declarative_base()

# MongoDB Connection
MONGO_URL = os.getenv("MONGODB_URL", "mongodb://mongoadmin:mongosecret@localhost:27017")
mongo_client = AsyncIOMotorClient(MONGO_URL)
mongo_db = mongo_client.saas_metadata
