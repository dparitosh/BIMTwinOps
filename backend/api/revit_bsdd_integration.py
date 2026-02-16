"""
Revit bSDD Plugin Integration Service

Coordinates integration between bSDD Revit plugin exports and BIMTwinOps knowledge graph.
Enables workflows:
1. Import IFC with bSDD classifications from Revit → Neo4j
2. Validate as-designed (BIM) vs as-built (Point Cloud)
3. Export enriched point cloud data back to IFC
"""
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

from .ifc_bsdd_parser import IFCBSDDParser, IFCBSDDParseResult, BSDDClassification
from .knowledge_graph_schema import KnowledgeGraphSchema
from .config import cfg

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of comparing BIM classification vs Point Cloud classification"""
    element_global_id: str
    element_name: Optional[str]
    element_type: str
    bim_classification: str
    point_cloud_classification: Optional[str]
    match_status: str  # "MATCH", "MISMATCH", "MISSING_PC", "MISSING_BIM"
    confidence: float
    spatial_overlap: float  # 0.0 to 1.0
    notes: List[str] = field(default_factory=list)


@dataclass
class IntegrationReport:
    """Comprehensive report of Revit-BIMTwinOps integration"""
    timestamp: str
    ifc_file: str
    total_bim_elements: int
    imported_classifications: int
    validation_results: List[ValidationResult]
    match_count: int
    mismatch_count: int
    missing_pc_count: int
    overall_accuracy: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class RevitBSDDIntegration:
    """
    Service for integrating bSDD Revit plugin exports with BIMTwinOps.
    Handles IFC import, classification mapping, and validation workflows.
    """
    
    def __init__(
        self,
        neo4j_uri: str = None,
        neo4j_user: str = None,
        neo4j_password: str = None,
        neo4j_database: str = None
    ):
        """Initialize integration service with knowledge graph connection"""
        self.kg = KnowledgeGraphSchema(
            neo4j_uri=neo4j_uri or cfg.NEO4J_URI,
            neo4j_user=neo4j_user or cfg.NEO4J_USER,
            neo4j_password=neo4j_password or cfg.NEO4J_PASSWORD,
            database=neo4j_database or cfg.NEO4J_DATABASE
        )
        self.parser = IFCBSDDParser()
        self._database = neo4j_database or cfg.NEO4J_DATABASE
    
    def import_ifc_with_bsdd(
        self,
        ifc_path: str,
        project_id: Optional[str] = None,
        merge_existing: bool = True
    ) -> Tuple[IFCBSDDParseResult, List[str]]:
        """
        Import an IFC file with bSDD classifications into Neo4j knowledge graph
        
        Args:
            ifc_path: Path to IFC file exported from Revit with bSDD plugin
            project_id: Optional project identifier for grouping
            merge_existing: If True, merge with existing classifications; if False, create new
            
        Returns:
            Tuple of (parse_result, list_of_created_node_ids)
        """
        logger.info(f"Importing IFC file with bSDD: {ifc_path}")
        
        # Step 1: Parse IFC file
        parse_result = self.parser.parse_file(ifc_path)
        
        if parse_result.errors:
            logger.error(f"Parse errors: {parse_result.errors}")
        
        if not parse_result.classifications:
            logger.warning("No bSDD classifications found in IFC file")
            return parse_result, []
        
        # Step 2: Import classifications into Neo4j
        created_nodes = []
        
        with self.kg.driver.session(database=self._database) as session:
            for classification in parse_result.classifications:
                try:
                    node_id = self._import_classification_to_neo4j(
                        session,
                        classification,
                        project_id,
                        merge_existing
                    )
                    created_nodes.append(node_id)
                except Exception as e:
                    error_msg = f"Failed to import {classification.code}: {str(e)}"
                    parse_result.errors.append(error_msg)
                    logger.error(error_msg)
        
        logger.info(f"Imported {len(created_nodes)} classifications to Neo4j")
        return parse_result, created_nodes
    
    def _import_classification_to_neo4j(
        self,
        session,
        classification: BSDDClassification,
        project_id: Optional[str],
        merge_existing: bool
    ) -> str:
        """Import a single bSDD classification into Neo4j"""
        
        # Create or merge RevitElement node
        query = """
        MERGE (re:RevitElement {globalId: $global_id})
        ON CREATE SET
            re.name = $element_name,
            re.ifcType = $ifc_type,
            re.created = datetime(),
            re.source = 'revit_bsdd_plugin'
        ON MATCH SET
            re.updated = datetime()
        SET
            re.projectId = $project_id
        
        // Link to bSDD class
        MERGE (bc:BsddClass {uri: $bsdd_uri})
        ON CREATE SET
            bc.code = $bsdd_code,
            bc.name = $bsdd_name,
            bc.source = 'revit_import'
        
        // Create relationship
        MERGE (re)-[r:CLASSIFIED_AS]->(bc)
        ON CREATE SET
            r.created = datetime(),
            r.dictionary = $dictionary,
            r.source = 'revit_bsdd_plugin'
        
        RETURN re.globalId as node_id
        """
        
        result = session.run(
            query,
            global_id=classification.element_global_id,
            element_name=classification.element_name,
            ifc_type=classification.ifc_entity_type,
            project_id=project_id,
            bsdd_uri=classification.uri,
            bsdd_code=classification.code,
            bsdd_name=classification.name,
            dictionary=classification.dictionary_name
        )
        
        record = result.single()
        return record["node_id"] if record else classification.element_global_id
    
    def validate_bim_vs_pointcloud(
        self,
        ifc_path: str,
        point_cloud_segments: List[Dict[str, Any]],
        spatial_tolerance: float = 0.5
    ) -> IntegrationReport:
        """
        Validate BIM classifications from Revit against point cloud classifications
        
        Args:
            ifc_path: Path to IFC file with bSDD classifications
            point_cloud_segments: List of point cloud segments with spatial data
            spatial_tolerance: Tolerance for spatial matching (meters)
            
        Returns:
            IntegrationReport with validation results
        """
        logger.info("Starting BIM vs Point Cloud validation")
        
        # Parse IFC
        parse_result = self.parser.parse_file(ifc_path)
        
        # Create report
        report = IntegrationReport(
            timestamp=datetime.utcnow().isoformat(),
            ifc_file=Path(ifc_path).name,
            total_bim_elements=parse_result.total_elements,
            imported_classifications=len(parse_result.classifications),
            validation_results=[],
            match_count=0,
            mismatch_count=0,
            missing_pc_count=0,
            overall_accuracy=0.0
        )
        
        # Validate each BIM element against point cloud
        for classification in parse_result.classifications:
            validation = self._validate_single_element(
                classification,
                point_cloud_segments,
                spatial_tolerance
            )
            
            report.validation_results.append(validation)
            
            # Update counters
            if validation.match_status == "MATCH":
                report.match_count += 1
            elif validation.match_status == "MISMATCH":
                report.mismatch_count += 1
            elif validation.match_status == "MISSING_PC":
                report.missing_pc_count += 1
        
        # Calculate overall accuracy
        total_validated = report.match_count + report.mismatch_count
        if total_validated > 0:
            report.overall_accuracy = report.match_count / total_validated * 100
        
        logger.info(f"Validation complete: {report.match_count} matches, "
                   f"{report.mismatch_count} mismatches, "
                   f"{report.missing_pc_count} missing from point cloud")
        
        return report
    
    def _validate_single_element(
        self,
        classification: BSDDClassification,
        point_cloud_segments: List[Dict[str, Any]],
        spatial_tolerance: float
    ) -> ValidationResult:
        """Validate a single BIM element against point cloud data"""
        
        # TODO: Implement spatial matching
        # For now, use simplified classification name matching
        
        # Extract IFC type (e.g., "IfcWall" -> "wall")
        ifc_type = classification.ifc_entity_type.replace("Ifc", "").lower()
        
        # Try to find matching point cloud segment
        # This is simplified - real implementation needs spatial bounding box matching
        matching_segment = None
        for segment in point_cloud_segments:
            pc_label = segment.get("semantic_label", "").lower()
            if ifc_type in pc_label or pc_label in ifc_type:
                matching_segment = segment
                break
        
        if not matching_segment:
            return ValidationResult(
                element_global_id=classification.element_global_id,
                element_name=classification.element_name,
                element_type=classification.ifc_entity_type,
                bim_classification=classification.code,
                point_cloud_classification=None,
                match_status="MISSING_PC",
                confidence=0.0,
                spatial_overlap=0.0,
                notes=["No spatially matching point cloud segment found"]
            )
        
        # Compare classifications
        pc_classification = matching_segment.get("semantic_label", "unknown")
        bim_code_lower = classification.code.lower()
        pc_label_lower = pc_classification.lower()
        
        # Check if classifications match
        is_match = (
            pc_label_lower in bim_code_lower or
            bim_code_lower in pc_label_lower or
            ifc_type in pc_label_lower
        )
        
        return ValidationResult(
            element_global_id=classification.element_global_id,
            element_name=classification.element_name,
            element_type=classification.ifc_entity_type,
            bim_classification=classification.code,
            point_cloud_classification=pc_classification,
            match_status="MATCH" if is_match else "MISMATCH",
            confidence=matching_segment.get("confidence", 0.0),
            spatial_overlap=1.0,  # Simplified
            notes=[]
        )
    
    def get_integration_statistics(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about Revit-BIMTwinOps integration"""
        
        with self.kg.driver.session(database=self._database) as session:
            query = """
            MATCH (re:RevitElement)-[r:CLASSIFIED_AS]->(bc:BsddClass)
            WHERE $project_id IS NULL OR re.projectId = $project_id
            RETURN
                count(DISTINCT re) as total_revit_elements,
                count(DISTINCT bc) as unique_bsdd_classes,
                count(r) as total_classifications,
                collect(DISTINCT bc.code) as bsdd_codes_used,
                collect(DISTINCT re.ifcType) as ifc_types_present
            """
            
            result = session.run(query, project_id=project_id)
            record = result.single()
            
            if not record:
                return {
                    "total_revit_elements": 0,
                    "unique_bsdd_classes": 0,
                    "total_classifications": 0,
                    "bsdd_codes_used": [],
                    "ifc_types_present": []
                }
            
            return {
                "total_revit_elements": record["total_revit_elements"],
                "unique_bsdd_classes": record["unique_bsdd_classes"],
                "total_classifications": record["total_classifications"],
                "bsdd_codes_used": record["bsdd_codes_used"],
                "ifc_types_present": record["ifc_types_present"]
            }
    
    def export_to_ifc(
        self,
        project_id: str,
        output_path: str,
        include_point_cloud_enrichment: bool = True
    ) -> str:
        """
        Export enriched data back to IFC format
        
        Args:
            project_id: Project to export
            output_path: Path for output IFC file
            include_point_cloud_enrichment: Include point cloud-derived data
            
        Returns:
            Path to created IFC file
        """
        # TODO: Implement IFC export
        # This requires ifcopenshell IFC writing capabilities
        raise NotImplementedError("IFC export not yet implemented")
    
    def clear_revit_imports(self, project_id: Optional[str] = None):
        """Clear imported Revit data from knowledge graph"""
        
        with self.kg.driver.session(database=self._database) as session:
            if project_id:
                query = """
                MATCH (re:RevitElement {projectId: $project_id})
                DETACH DELETE re
                """
                session.run(query, project_id=project_id)
            else:
                query = """
                MATCH (re:RevitElement)
                DETACH DELETE re
                """
                session.run(query)
        
        logger.info(f"Cleared Revit imports for project: {project_id or 'ALL'}")
