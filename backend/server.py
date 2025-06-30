from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import aiofiles
import tempfile
import base64
import json
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import requests
import secrets

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Collections
sessions_collection = db.whatsapp_sessions
bot_status_collection = db.bot_status

# Create the main app without a prefix
app = FastAPI(title="WhatsApp Bot with Mega.nz Storage", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class SessionFile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_data: str  # Base64 encoded file data
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

# Simple file storage system (for demonstration - in production, use proper cloud storage)
class SimpleFileStorage:
    def __init__(self):
        self.storage_dir = Path("session_storage")
        self.storage_dir.mkdir(exist_ok=True)
    
    async def store_file(self, filename: str, content: bytes) -> str:
        """Store file and return unique file ID"""
        file_id = f"{uuid.uuid4().hex}_{filename}"
        file_path = self.storage_dir / file_id
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        return file_id
    
    async def retrieve_file(self, file_id: str) -> bytes:
        """Retrieve file content by file ID"""
        file_path = self.storage_dir / file_id
        
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_id} not found")
        
        async with aiofiles.open(file_path, 'rb') as f:
            return await f.read()
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file by file ID"""
        file_path = self.storage_dir / file_id
        
        if file_path.exists():
            file_path.unlink()
            return True
        return False

# Initialize file storage
file_storage = SimpleFileStorage()

# Session Management Routes
@api_router.post("/sessions/upload")
async def upload_session_file(file: UploadFile = File(...)):
    """Upload WhatsApp session file to storage"""
    try:
        # Read file contents
        contents = await file.read()
        
        # Store file using our simple storage
        stored_file_id = await file_storage.store_file(file.filename, contents)
        
        # Store metadata in database
        session_data = SessionFile(
            filename=file.filename,
            file_data=stored_file_id,  # Store file ID instead of base64 for efficiency
            file_size=len(contents)
        )
        
        # Insert into database
        await sessions_collection.insert_one(session_data.dict())
        
        logger.info(f"Successfully uploaded session file: {file.filename}")
        return {
            "success": True,
            "message": "Session file uploaded successfully",
            "file_id": stored_file_id,
            "filename": file.filename
        }
            
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
    """Download session file from storage"""
    try:
        # Find session in database
        session_data = await sessions_collection.find_one({"file_data": file_id})
        if not session_data:
            raise HTTPException(status_code=404, detail="Session file not found")
        
        # Create downloads directory
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        
        # Retrieve file content
        file_content = await file_storage.retrieve_file(file_id)
        
        # Save to downloads directory
        download_path = downloads_dir / session_data['filename']
        async with aiofiles.open(download_path, 'wb') as f:
            await f.write(file_content)
        
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
    """Delete session file from both storage and database"""
    try:
        # Remove from database first
        result = await sessions_collection.delete_one({"file_data": file_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Session file not found")
        
        # Delete from storage
        await file_storage.delete_file(file_id)
        
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
    """Restore the most recent session from storage"""
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
        
        # Retrieve file content
        file_content = await file_storage.retrieve_file(latest_session['file_data'])
        
        # Save to downloads directory
        download_path = downloads_dir / latest_session['filename']
        async with aiofiles.open(download_path, 'wb') as f:
            await f.write(file_content)
        
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
    return {
        "status": "healthy",
        "storage_available": True,
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
    logger.info("Starting WhatsApp Bot with Session Storage...")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Clean up connections on shutdown"""
    client.close()
    logger.info("Application shut down")