from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import aiofiles
import tempfile
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
from mega import Mega
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Collections
sessions_collection = db.whatsapp_sessions
bot_status_collection = db.bot_status

# Mega.nz setup
mega = Mega()
mega_client = None

# Create the main app without a prefix
app = FastAPI(title="WhatsApp Bot with Mega.nz Storage", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class SessionFile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    mega_file_id: str
    mega_link: str
    file_size: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class BotStatus(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_connected: bool = False
    phone_number: Optional[str] = None
    qr_code: Optional[str] = None
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    session_restored: bool = False

class WhatsAppMessage(BaseModel):
    from_number: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Initialize Mega.nz connection
async def init_mega():
    global mega_client
    try:
        mega_email = os.getenv('MEGA_EMAIL')
        mega_password = os.getenv('MEGA_PASSWORD')
        
        if not mega_email or not mega_password:
            logger.error("Mega.nz credentials not found in environment variables")
            return False
            
        loop = asyncio.get_running_loop()
        mega_client = await loop.run_in_executor(None, mega.login, mega_email, mega_password)
        logger.info("Successfully connected to Mega.nz")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Mega.nz: {str(e)}")
        return False

# Session Management Routes
@api_router.post("/sessions/upload")
async def upload_session_file(file: UploadFile = File(...)):
    """Upload WhatsApp session file to Mega.nz"""
    if not mega_client:
        raise HTTPException(status_code=503, detail="Mega.nz not connected")
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            # Read and write file contents
            contents = await file.read()
            temp_file.write(contents)
            temp_file_path = temp_file.name
        
        try:
            # Upload to Mega.nz
            loop = asyncio.get_running_loop()
            mega_file = await loop.run_in_executor(None, mega_client.upload, temp_file_path)
            public_link = await loop.run_in_executor(None, mega_client.get_upload_link, mega_file)
            
            # Store metadata in database
            session_data = SessionFile(
                filename=file.filename,
                mega_file_id=mega_file['h'],
                mega_link=public_link,
                file_size=len(contents)
            )
            
            # Insert into database
            await sessions_collection.insert_one(session_data.dict())
            
            logger.info(f"Successfully uploaded session file: {file.filename}")
            return {
                "success": True,
                "message": "Session file uploaded successfully",
                "file_id": mega_file['h'],
                "public_link": public_link
            }
            
        finally:
            # Cleanup temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Failed to upload session file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@api_router.get("/sessions")
async def list_session_files():
    """List all stored session files"""
    try:
        sessions = []
        async for session in sessions_collection.find():
            # Convert ObjectId to string for JSON serialization
            session['_id'] = str(session['_id'])
            sessions.append(SessionFile(**session))
        
        return {
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        }
    except Exception as e:
        logger.error(f"Failed to list sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

@api_router.get("/sessions/download/{file_id}")
async def download_session_file(file_id: str):
    """Download session file from Mega.nz"""
    if not mega_client:
        raise HTTPException(status_code=503, detail="Mega.nz not connected")
    
    try:
        # Find session in database
        session_data = await sessions_collection.find_one({"mega_file_id": file_id})
        if not session_data:
            raise HTTPException(status_code=404, detail="Session file not found")
        
        # Create downloads directory
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        
        # Download from Mega.nz
        loop = asyncio.get_running_loop()
        download_path = downloads_dir / session_data['filename']
        await loop.run_in_executor(None, mega_client.download, file_id, str(downloads_dir))
        
        logger.info(f"Successfully downloaded session file: {session_data['filename']}")
        return {
            "success": True,
            "message": "Session file downloaded successfully",
            "local_path": str(download_path),
            "filename": session_data['filename']
        }
        
    except Exception as e:
        logger.error(f"Failed to download session file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@api_router.delete("/sessions/{file_id}")
async def delete_session_file(file_id: str):
    """Delete session file from both Mega.nz and database"""
    if not mega_client:
        raise HTTPException(status_code=503, detail="Mega.nz not connected")
    
    try:
        # Remove from database first
        result = await sessions_collection.delete_one({"mega_file_id": file_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Session file not found")
        
        # Delete from Mega.nz
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, mega_client.delete, file_id)
        
        logger.info(f"Successfully deleted session file: {file_id}")
        return {
            "success": True,
            "message": "Session file deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete session file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

# Bot Status Routes
@api_router.get("/bot/status")
async def get_bot_status():
    """Get current bot connection status"""
    try:
        status = await bot_status_collection.find_one({}, sort=[("last_seen", -1)])
        if status:
            status['_id'] = str(status['_id'])
            return BotStatus(**status)
        else:
            # Return default status
            default_status = BotStatus()
            await bot_status_collection.insert_one(default_status.dict())
            return default_status
    except Exception as e:
        logger.error(f"Failed to get bot status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get bot status: {str(e)}")

@api_router.post("/bot/status")
async def update_bot_status(status: BotStatus):
    """Update bot connection status"""
    try:
        # Update or insert bot status
        await bot_status_collection.update_one(
            {"id": status.id},
            {"$set": status.dict()},
            upsert=True
        )
        
        logger.info(f"Bot status updated: connected={status.is_connected}")
        return {
            "success": True,
            "message": "Bot status updated successfully"
        }
    except Exception as e:
        logger.error(f"Failed to update bot status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update bot status: {str(e)}")

# Session Restoration
@api_router.post("/bot/restore-session")
async def restore_latest_session():
    """Restore the most recent session from Mega.nz"""
    if not mega_client:
        raise HTTPException(status_code=503, detail="Mega.nz not connected")
    
    try:
        # Find the most recent session
        latest_session = await sessions_collection.find_one({}, sort=[("created_at", -1)])
        if not latest_session:
            return {
                "success": False,
                "message": "No session files found to restore"
            }
        
        # Download the session file
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, 
            mega_client.download, 
            latest_session['mega_file_id'], 
            str(downloads_dir)
        )
        
        # Update bot status to indicate session restored
        await bot_status_collection.update_one(
            {},
            {"$set": {"session_restored": True, "last_seen": datetime.utcnow()}},
            upsert=True
        )
        
        logger.info(f"Successfully restored session: {latest_session['filename']}")
        return {
            "success": True,
            "message": f"Session restored: {latest_session['filename']}",
            "filename": latest_session['filename']
        }
        
    except Exception as e:
        logger.error(f"Failed to restore session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Session restoration failed: {str(e)}")

# WhatsApp Bot Simulation Routes (for demonstration)
@api_router.post("/bot/generate-qr")
async def generate_qr_code():
    """Generate a mock QR code for WhatsApp authentication"""
    import secrets
    mock_qr = f"whatsapp-auth-{secrets.token_hex(16)}"
    
    # Update bot status with QR code
    await bot_status_collection.update_one(
        {},
        {"$set": {
            "qr_code": mock_qr,
            "is_connected": False,
            "last_seen": datetime.utcnow()
        }},
        upsert=True
    )
    
    return {
        "success": True,
        "qr_code": mock_qr,
        "message": "QR code generated (mock for demonstration)"
    }

@api_router.post("/bot/connect")
async def simulate_whatsapp_connection():
    """Simulate WhatsApp connection after QR scan"""
    await bot_status_collection.update_one(
        {},
        {"$set": {
            "is_connected": True,
            "phone_number": "+1234567890",
            "qr_code": None,
            "last_seen": datetime.utcnow()
        }},
        upsert=True
    )
    
    return {
        "success": True,
        "message": "WhatsApp connected successfully (simulated)"
    }

# Health check
@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    mega_status = mega_client is not None
    return {
        "status": "healthy",
        "mega_connected": mega_status,
        "timestamp": datetime.utcnow()
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    logger.info("Starting WhatsApp Bot with Mega.nz Storage...")
    await init_mega()

@app.on_event("shutdown")
async def shutdown_db_client():
    """Clean up connections on shutdown"""
    client.close()
    logger.info("Application shut down")