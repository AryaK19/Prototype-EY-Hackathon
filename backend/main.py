from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging
from contextlib import asynccontextmanager

# Suppress uvicorn reload logs
logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.ERROR)
logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
logging.getLogger("uvicorn.access").setLevel(logging.ERROR)

# Import routers
from routers import doctor_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Create necessary directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    yield
    
    # Shutdown
    pass

# Create FastAPI app
app = FastAPI(
    title="EY Hackathon - Doctor Verification API",
    description="API for verifying doctor credentials and information through multiple data sources",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173", "https://vxswjtsw-5173.inc1.devtunnels.ms"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(doctor_router.router)

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "EY Hackathon - Doctor Verification API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "doctor_verification": "/api/doctor/verify",
            "doctor_search": "/api/doctor/search",
            "pdf_extraction": "/api/doctor/extract-pdf",
            "specialties": "/api/doctor/specialties",
            "insurance_networks": "/api/doctor/insurance-networks"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Doctor Verification API is running",
        "timestamp": "2024-12-07"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="error",
        access_log=False,
        reload_delay=0.5
    )