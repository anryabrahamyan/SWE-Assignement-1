from fastapi import Request, HTTPException
from database import WriterSessionLocal, Reader1SessionLocal, Reader2SessionLocal
import logging

logger = logging.getLogger(__name__)

def get_writer_db():
    db = WriterSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_tenant_id_from_request(request: Request) -> int:
    """Mock extractor: in reality this extracts tenant_id from JWT payload"""
    tenant_id_header = request.headers.get("X-Tenant-ID")
    if not tenant_id_header:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header missing")
    try:
        return int(tenant_id_header)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Tenant ID")

def get_reader_db(request: Request):
    """
    Application-Level Sharding Logic for Reads
    Modulo logic to distribute heavy analytics workloads.
    """
    tenant_id = get_tenant_id_from_request(request)
    total_shards = 2 # We have 2 read replicas
    shard_id = tenant_id % total_shards
    
    logger.info(f"Routing read request for tenant {tenant_id} to shard {shard_id}")
    
    if shard_id == 0:
        db = Reader1SessionLocal()
    else:
        db = Reader2SessionLocal()
        
    try:
        yield db
    finally:
        db.close()
