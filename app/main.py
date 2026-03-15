import os
import io
import uuid
import datetime
import logging
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import google.generativeai as genai

from database import writer_engine, mongo_db, Base
from models import Tenant, User, Transaction, ImageJob
from sharding import get_writer_db, get_reader_db, get_tenant_id_from_request

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(title="Multi-Tenant Image Classifier API")

# Setup upload directory
UPLOAD_DIR = "/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Try setting up Gemini Pro Vision
try:
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and gemini_key != "YOUR_API_KEY_HERE":
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')  # Stable vision-capable model
    else:
        model = None
except ImportError:
    model = None

@app.on_event("startup")
def startup_event():
    logger.info("Starting up FastAPI. Initializing Primary DB Schema...")
    # Initialize SQLAlchemy tables on Primary DB. Replicas will stream this.
    try:
        Base.metadata.create_all(bind=writer_engine)
        logger.info("Schema initialized.")
    except Exception as e:
        logger.error(f"Error initializing schema: {e}")

@app.post("/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    writer_db: Session = Depends(get_writer_db),
    tenant_id: int = Depends(get_tenant_id_from_request)
):
    """
    1. Verify tenant & billing (omitted strict billing limit for brevity)
    2. Save image to disk
    3. Log 'PENDING' job in Primary DB (ACID constraint)
    4. Call Gemini Model
    5. Save results to MongoDB (NoSQL)
    6. Update job to 'COMPLETED' in Primary DB
    """
    logger.info(f"Processing upload for Tenant {tenant_id}")
    
    # Verify Tenant
    tenant = writer_db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    # Create billing transaction (ACID transaction simulation)
    tx = Transaction(tenant_id=tenant_id, amount=1.00, status="PENDING")
    writer_db.add(tx)
    
    # Save file
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        writer_db.rollback()
        raise HTTPException(status_code=500, detail="File save failed")
        
    # Log job in Primary DB
    job = ImageJob(tenant_id=tenant_id, file_path=file_path, status="PENDING")
    writer_db.add(job)
    writer_db.commit()
    writer_db.refresh(job)
    
    tx.status = "COMPLETED"
    writer_db.commit()

    # Call Gemini (or mock if not configured)
    hashtags = []
    if model:
        try:
            from PIL import Image
            # We must seek back to 0 because `await file.read()` earlier advanced the file pointer 
            # OR we just re-read it from disk since we explicitly saved it in the steps above
            img = Image.open(file_path)
            response = model.generate_content(["Provide 5 concise hashtags describing this image.", img])
            hashtags = [h.strip() for h in response.text.split("\n") if h.strip()]
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            hashtags = ["#error", f"#errormsg:{str(e)[:50].replace(' ', '_')}"]
    else:
        hashtags = ["#mock", "#image", "#processed"]
        
    # Save Results to MongoDB for fast long-term querying and analytics
    mongo_doc = {
        "job_id": job.id,
        "tenant_id": tenant_id,
        "file_path": file_path,
        "hashtags": hashtags,
        "created_at": datetime.datetime.utcnow()
    }
    await mongo_db.image_results.insert_one(mongo_doc)
    
    # Update state in Primary DB
    job.status = "COMPLETED"
    writer_db.commit()
    
    return {"message": "Image processed successfully", "job_id": job.id, "hashtags": hashtags}


@app.get("/history")
async def get_history(
    request: Request,
    limit: int = 10,
    skip: int = 0,
    reader_db: Session = Depends(get_reader_db),
    tenant_id: int = Depends(get_tenant_id_from_request)
):
    """
    Retrieves history directly hitting the Sharded Read Replica
    and combining with MongoDB NoSQL Document Store metadata.
    """
    logger.info(f"Querying history for Tenant: {tenant_id} on Replica Shard.")
    
    # Query Relational Data from Read-Replica
    jobs = reader_db.query(ImageJob).filter(ImageJob.tenant_id == tenant_id).order_by(ImageJob.created_at.desc()).offset(skip).limit(limit).all()
    job_ids = [j.id for j in jobs]
    
    # Query Metadata from MongoDB
    cursor = mongo_db.image_results.find({"job_id": {"$in": job_ids}})
    mongo_results = await cursor.to_list(length=limit)
    
    # Map Mongo results by job_id
    results_map = {doc["job_id"]: doc["hashtags"] for doc in mongo_results}
    
    response_data = []
    for job in jobs:
        response_data.append({
            "job_id": job.id,
            "status": job.status,
            "file_path": job.file_path,
            "created_at": job.created_at,
            "hashtags": results_map.get(job.id, [])
        })
        
    return {
        "tenant_id": tenant_id,
        "results": response_data,
        "source": "PostgreSQL Replica & MongoDB"
    }

@app.get("/debug/gemini")
async def debug_gemini():
    """Temporary debug endpoint to test Gemini directly from inside the container."""
    if not model:
        return {"status": "error", "detail": "model is None — GEMINI_API_KEY not set or import failed"}
    try:
        from PIL import Image
        import io
        # Use a tiny 1x1 white pixel to test the API connection
        img = Image.new('RGB', (10, 10), color='white')
        response = model.generate_content(["Reply with exactly: #test #ok #gemini #working #success", img])
        return {"status": "success", "response": response.text}
    except Exception as e:
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
        except Exception as e2:
            available_models = [f"Failed to list: {str(e2)}"]
            
        return {
            "status": "error", 
            "error_type": type(e).__name__, 
            "detail": str(e),
            "available_models": available_models
        }
