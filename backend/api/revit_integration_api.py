"""
Revit bSDD Plugin Integration API Endpoints

Provides REST API for integrating IFC files exported from bSDD Revit plugin.
Supports import, validation, and workflow coordination.
"""
import logging
import os
import shutil
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .revit_bsdd_integration import RevitBSDDIntegration, ValidationResult, IntegrationReport
from .ifc_bsdd_parser import IFCBSDDParseResult, BSDDClassification
from .config import cfg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/revit-integration", tags=["Revit Integration"])

# Upload directory for IFC files
UPLOAD_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "uploads" / "ifc"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class IFCUploadResponse(BaseModel):
    """Response after uploading IFC file"""
    file_id: str
    file_name: str
    file_size: int
    uploaded_at: str
    status: str
    message: str


class IFCParseResponse(BaseModel):
    """Response after parsing IFC file"""
    file_name: str
    ifc_schema: str
    total_elements: int
    classified_elements: int
    classification_coverage: float
    dictionaries_used: List[str]
    classifications_by_type: Dict[str, int]
    bsdd_classifications: int
    errors: List[str]
    warnings: List[str]


class ImportRequest(BaseModel):
    """Request to import IFC classifications into Neo4j"""
    file_id: str
    project_id: Optional[str] = None
    merge_existing: bool = True


class ImportResponse(BaseModel):
    """Response after importing IFC to Neo4j"""
    file_name: str
    imported_count: int
    created_nodes: List[str]
    errors: List[str]
    warnings: List[str]
    status: str


class ValidationRequest(BaseModel):
    """Request to validate BIM vs Point Cloud"""
    file_id: str
    point_cloud_segments: List[Dict[str, Any]]
    spatial_tolerance: float = 0.5


class ValidationResponse(BaseModel):
    """Response with validation results"""
    timestamp: str
    ifc_file: str
    total_bim_elements: int
    match_count: int
    mismatch_count: int
    missing_pc_count: int
    overall_accuracy: float
    validation_results: List[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]


# Initialize integration service
integration_service = RevitBSDDIntegration()


@router.post("/upload-ifc", response_model=IFCUploadResponse)
async def upload_ifc_file(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None)
):
    """
    Upload an IFC file exported from Revit with bSDD plugin
    
    Args:
        file: IFC file (multipart/form-data)
        project_id: Optional project identifier
        
    Returns:
        Upload confirmation with file_id for subsequent operations
    """
    # Validate file extension
    if not file.filename.lower().endswith('.ifc'):
        raise HTTPException(
            status_code=400,
            detail="Only IFC files are supported (.ifc extension)"
        )
    
    # Generate unique file ID
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_id = f"{timestamp}_{file.filename}"
    file_path = UPLOAD_DIR / file_id
    
    try:
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(file_path)
        
        logger.info(f"Uploaded IFC file: {file_id} ({file_size} bytes)")
        
        return IFCUploadResponse(
            file_id=file_id,
            file_name=file.filename,
            file_size=file_size,
            uploaded_at=datetime.utcnow().isoformat(),
            status="success",
            message=f"File uploaded successfully: {file.filename}"
        )
        
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/parse-ifc/{file_id}", response_model=IFCParseResponse)
async def parse_ifc_file(file_id: str):
    """
    Parse an uploaded IFC file to extract bSDD classifications
    
    Args:
        file_id: File ID from upload response
        
    Returns:
        Parse results with classifications statistics
    """
    file_path = UPLOAD_DIR / file_id
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    
    try:
        # Parse IFC file
        parse_result = integration_service.parser.parse_file(str(file_path))
        
        # Generate statistics
        stats = integration_service.parser.get_statistics(parse_result)
        
        return IFCParseResponse(
            file_name=parse_result.file_name,
            ifc_schema=parse_result.ifc_schema,
            total_elements=parse_result.total_elements,
            classified_elements=parse_result.classified_elements,
            classification_coverage=stats["classification_coverage"],
            dictionaries_used=list(parse_result.dictionaries_used),
            classifications_by_type=stats["classifications_by_type"],
            bsdd_classifications=stats["bsdd_classifications"],
            errors=parse_result.errors,
            warnings=parse_result.warnings
        )
        
    except Exception as e:
        logger.error(f"Failed to parse IFC: {e}")
        raise HTTPException(status_code=500, detail=f"Parse failed: {str(e)}")


@router.post("/import-to-neo4j", response_model=ImportResponse)
async def import_ifc_to_neo4j(request: ImportRequest):
    """
    Import bSDD classifications from IFC file into Neo4j knowledge graph
    
    Args:
        request: Import configuration
        
    Returns:
        Import results with created node IDs
    """
    file_path = UPLOAD_DIR / request.file_id
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_id}")
    
    try:
        # Import to Neo4j
        parse_result, created_nodes = integration_service.import_ifc_with_bsdd(
            str(file_path),
            project_id=request.project_id,
            merge_existing=request.merge_existing
        )
        
        return ImportResponse(
            file_name=parse_result.file_name,
            imported_count=len(created_nodes),
            created_nodes=created_nodes[:100],  # Limit response size
            errors=parse_result.errors,
            warnings=parse_result.warnings,
            status="success" if created_nodes else "no_data"
        )
        
    except Exception as e:
        logger.error(f"Failed to import to Neo4j: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/validate-bim-vs-pointcloud", response_model=ValidationResponse)
async def validate_bim_vs_pointcloud(request: ValidationRequest):
    """
    Validate BIM classifications from Revit against point cloud classifications
    
    Args:
        request: Validation configuration with file_id and point cloud data
        
    Returns:
        Validation report with match/mismatch analysis
    """
    file_path = UPLOAD_DIR / request.file_id
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_id}")
    
    try:
        # Run validation
        report = integration_service.validate_bim_vs_pointcloud(
            str(file_path),
            request.point_cloud_segments,
            request.spatial_tolerance
        )
        
        # Convert validation results to dicts
        validation_dicts = [
            {
                "element_global_id": v.element_global_id,
                "element_name": v.element_name,
                "element_type": v.element_type,
                "bim_classification": v.bim_classification,
                "point_cloud_classification": v.point_cloud_classification,
                "match_status": v.match_status,
                "confidence": v.confidence,
                "spatial_overlap": v.spatial_overlap,
                "notes": v.notes
            }
            for v in report.validation_results
        ]
        
        return ValidationResponse(
            timestamp=report.timestamp,
            ifc_file=report.ifc_file,
            total_bim_elements=report.total_bim_elements,
            match_count=report.match_count,
            mismatch_count=report.mismatch_count,
            missing_pc_count=report.missing_pc_count,
            overall_accuracy=report.overall_accuracy,
            validation_results=validation_dicts[:100],  # Limit response
            errors=report.errors,
            warnings=report.warnings
        )
        
    except Exception as e:
        logger.error(f"Failed to validate: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/integration-stats")
async def get_integration_statistics(project_id: Optional[str] = None):
    """
    Get statistics about Revit-BIMTwinOps integration
    
    Args:
        project_id: Optional filter by project
        
    Returns:
        Statistics about imported Revit elements and bSDD classifications
    """
    try:
        stats = integration_service.get_integration_statistics(project_id)
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Statistics failed: {str(e)}")


@router.get("/uploaded-files")
async def list_uploaded_files():
    """List all uploaded IFC files"""
    try:
        files = []
        for file_path in UPLOAD_DIR.glob("*.ifc"):
            stat = file_path.stat()
            files.append({
                "file_id": file_path.name,
                "file_name": file_path.name,
                "file_size": stat.st_size,
                "uploaded_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
        
        return JSONResponse(content={"files": files, "count": len(files)})
        
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=f"List failed: {str(e)}")


@router.delete("/clear-imports")
async def clear_revit_imports(project_id: Optional[str] = None):
    """
    Clear imported Revit data from Neo4j
    
    Args:
        project_id: Optional filter by project (clears all if not provided)
        
    Returns:
        Confirmation message
    """
    try:
        integration_service.clear_revit_imports(project_id)
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Cleared Revit imports for project: {project_id or 'ALL'}"
        })
        
    except Exception as e:
        logger.error(f"Failed to clear imports: {e}")
        raise HTTPException(status_code=500, detail=f"Clear failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check for Revit integration service"""
    try:
        # Test Neo4j connection
        stats = integration_service.get_integration_statistics()
        
        return JSONResponse(content={
            "status": "healthy",
            "neo4j_connected": True,
            "upload_directory": str(UPLOAD_DIR),
            "revit_elements_imported": stats["total_revit_elements"]
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )
