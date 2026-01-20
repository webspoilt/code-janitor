"""
Code Janitor Web Application.
"""

import os
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

from janitor.db.session import init_db, get_db, SessionLocal
from janitor.core.resources import ResourceManager
from janitor.core.linter import Linter
from janitor.core.analyzer import Analyzer
from janitor.core.refactorer import Refactorer
from janitor.config import Config
from janitor.db.models import AnalysisRecord

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("janitor.web")

# Resource Manager Singleton
resource_manager = ResourceManager()

# Database Init
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Code Janitor Web...")
    init_db()
    yield
    logger.info("Shutting down...")

app = FastAPI(title="Code Janitor Web", lifespan=lifespan)

# Directories
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"

# Create directories if not exist
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

# Mounts
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# Config (Load once)
config = Config.load()

# ==========================================
# Routes
# ==========================================

@app.get("/")
async def index(request: Request):
    """Serve the main UI."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/hardware/status")
async def hardware_status():
    """Get real-time hardware status."""
    return resource_manager.get_status()

@app.post("/api/analyze")
async def analyze_file(file: UploadFile = File(...)):
    """Analyze an uploaded file."""
    try:
        content = await file.read()
        code = content.decode('utf-8')
        
        # Create temp file for analysis (tools expect path)
        temp_path = Path(f"temp_{file.filename}")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        try:
            # 1. Lint
            linter = Linter(config)
            lint_result = linter.analyze(temp_path, auto_fix=False)
            
            # 2. Static Analysis
            analyzer = Analyzer(config)
            analysis_result = analyzer.analyze(temp_path)
            
            # Save record to DB
            db = SessionLocal()
            record = AnalysisRecord(
                filename=file.filename,
                total_issues=analysis_result.issue_count + len(lint_result.issues),
                security_issues_count=len(analysis_result.security_issues),
                code_smells_count=len(analysis_result.code_smells),
                issues_data={
                    "security": analysis_result.security_issues,
                    "smells": analysis_result.code_smells,
                    "lint": lint_result.issues
                }
            )
            db.add(record)
            db.commit()
            db.close()
            
            return {
                "success": True,
                "filename": file.filename,
                "issues": lint_result.issues if lint_result.has_issues else [],
                "security_issues": analysis_result.security_issues,
                "code_smells": analysis_result.code_smells,
                "summary": {
                    "total": analysis_result.issue_count + len(lint_result.issues),
                    "security_count": len(analysis_result.security_issues)
                }
            }
            
        finally:
            if temp_path.exists():
                temp_path.unlink()
                
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/ai/refactor")
async def ai_refactor(request: dict):
    """Refactor code using configured AI."""
    code = request.get("code")
    issues = request.get("issues", []) # text description of issues
    
    if not code:
        return JSONResponse(status_code=400, content={"error": "No code provided"})

    # Create temp file
    temp_path = Path("temp_refactor.py") 
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(code)
        
    try:
        # We need analysis result objects to pass to refactorer. 
        # Since we just have raw text, we re-run analysis locally or mock the object.
        # For robustness, let's re-run analyzer on this content.
        
        analyzer = Analyzer(config)
        analysis_result = analyzer.analyze(temp_path)
        
        linter = Linter(config)
        lint_result = linter.analyze(temp_path)
        
        refactorer = Refactorer(config)
        result = refactorer.refactor(temp_path, analysis_result, lint_result)
        
        if result.success:
            return {"success": True, "response": result.refactored_code}
        else:
            return {"success": False, "error": result.error}
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        if temp_path.exists():
            temp_path.unlink()

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket for Real-time Hardware Stats."""
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(2)
            stats = resource_manager.get_status()
            await websocket.send_json({
                "type": "heartbeat",
                "data": stats
            })
    except WebSocketDisconnect:
        pass
