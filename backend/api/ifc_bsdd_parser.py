"""
IFC bSDD Classification Parser

Parses IFC files to extract buildingSMART Data Dictionary (bSDD) classifications
from IfcClassificationReference entities, compatible with bSDD Revit plugin exports.
"""
import logging
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from pathlib import Path
import ifcopenshell
import ifcopenshell.util.element

logger = logging.getLogger(__name__)


@dataclass
class BSDDClassification:
    """Represents a bSDD classification extracted from IFC"""
    uri: str
    code: str
    name: str
    ifc_entity_type: str  # IfcWall, IfcDoor, etc.
    element_global_id: str
    element_name: Optional[str] = None
    dictionary_name: Optional[str] = None
    dictionary_version: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IFCBSDDParseResult:
    """Results from parsing an IFC file for bSDD classifications"""
    file_name: str
    total_elements: int
    classified_elements: int
    classifications: List[BSDDClassification]
    dictionaries_used: Set[str]
    ifc_schema: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class IFCBSDDParser:
    """
    Parser for extracting bSDD classifications from IFC files.
    Compatible with bSDD Revit plugin export format.
    """
    
    def __init__(self):
        self.ifc_file = None
        self.classifications = []
        self.dictionaries = {}
        
    def parse_file(self, ifc_path: str) -> IFCBSDDParseResult:
        """
        Parse an IFC file and extract all bSDD classifications
        
        Args:
            ifc_path: Path to IFC file
            
        Returns:
            IFCBSDDParseResult with extracted classifications
        """
        logger.info(f"Parsing IFC file: {ifc_path}")
        
        try:
            self.ifc_file = ifcopenshell.open(ifc_path)
        except Exception as e:
            logger.error(f"Failed to open IFC file: {e}")
            return IFCBSDDParseResult(
                file_name=Path(ifc_path).name,
                total_elements=0,
                classified_elements=0,
                classifications=[],
                dictionaries_used=set(),
                ifc_schema="UNKNOWN",
                errors=[f"Failed to open IFC file: {str(e)}"]
            )
        
        result = IFCBSDDParseResult(
            file_name=Path(ifc_path).name,
            total_elements=0,
            classified_elements=0,
            classifications=[],
            dictionaries_used=set(),
            ifc_schema=self.ifc_file.schema
        )
        
        # Step 1: Extract all IfcClassification dictionaries
        self._extract_dictionaries()
        
        # Step 2: Extract IfcRelAssociatesClassification relationships
        classification_rels = self.ifc_file.by_type("IfcRelAssociatesClassification")
        
        if not classification_rels:
            result.warnings.append("No IfcRelAssociatesClassification found in file")
            logger.warning("No classification relationships found")
        
        # Step 3: Process each classification relationship
        for rel in classification_rels:
            try:
                self._process_classification_rel(rel, result)
            except Exception as e:
                error_msg = f"Error processing classification relationship: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg)
        
        # Step 4: Count total building elements
        building_elements = self._get_building_elements()
        result.total_elements = len(building_elements)
        result.classified_elements = len(result.classifications)
        result.dictionaries_used = set(self.dictionaries.keys())
        
        logger.info(f"Parsed {result.classified_elements}/{result.total_elements} classified elements")
        logger.info(f"Found {len(result.dictionaries_used)} dictionaries: {result.dictionaries_used}")
        
        return result
    
    def _extract_dictionaries(self):
        """Extract all IfcClassification dictionaries from the file"""
        classifications = self.ifc_file.by_type("IfcClassification")
        
        for classification in classifications:
            name = getattr(classification, "Name", None)
            if name:
                self.dictionaries[name] = {
                    "name": name,
                    "source": getattr(classification, "Source", None),
                    "edition": getattr(classification, "Edition", None),
                    "edition_date": getattr(classification, "EditionDate", None),
                    "description": getattr(classification, "Description", None),
                }
                logger.debug(f"Found dictionary: {name}")
    
    def _process_classification_rel(
        self,
        rel: Any,
        result: IFCBSDDParseResult
    ):
        """Process a single IfcRelAssociatesClassification relationship"""
        classification_ref = rel.RelatingClassification
        
        # Get classification details
        classification_uri = None
        classification_code = None
        classification_name = None
        dictionary_name = None
        
        # IfcClassificationReference structure
        if classification_ref.is_a("IfcClassificationReference"):
            # Location is typically the URI
            classification_uri = getattr(classification_ref, "Location", None)
            classification_code = getattr(classification_ref, "Identification", None)
            classification_name = getattr(classification_ref, "Name", None)
            
            # Get parent dictionary
            ref_source = getattr(classification_ref, "ReferencedSource", None)
            if ref_source and ref_source.is_a("IfcClassification"):
                dictionary_name = getattr(ref_source, "Name", None)
        
        # Skip if no URI (not a bSDD classification)
        if not classification_uri:
            result.warnings.append(
                f"Classification reference without URI: {classification_code}"
            )
            return
        
        # Check if this is a buildingSMART bSDD URI
        if "identifier.buildingsmart.org" not in classification_uri:
            result.warnings.append(
                f"Non-bSDD URI found: {classification_uri}"
            )
            # Still process it, but note it's not standard bSDD
        
        # Process all related objects (building elements)
        for obj in rel.RelatedObjects:
            try:
                element_type = obj.is_a()
                global_id = obj.GlobalId
                element_name = getattr(obj, "Name", None)
                
                # Extract properties if available
                properties = self._extract_element_properties(obj)
                
                # Create classification record
                bsdd_class = BSDDClassification(
                    uri=classification_uri,
                    code=classification_code or "UNKNOWN",
                    name=classification_name or "Unnamed",
                    ifc_entity_type=element_type,
                    element_global_id=global_id,
                    element_name=element_name,
                    dictionary_name=dictionary_name,
                    properties=properties
                )
                
                result.classifications.append(bsdd_class)
                logger.debug(f"Extracted: {element_type} -> {classification_code}")
                
            except Exception as e:
                error_msg = f"Error processing element {obj}: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg)
    
    def _extract_element_properties(self, element: Any) -> Dict[str, Any]:
        """Extract properties from an IFC element"""
        properties = {}
        
        try:
            # Get property sets
            psets = ifcopenshell.util.element.get_psets(element)
            
            for pset_name, pset_data in psets.items():
                # Skip metadata keys
                filtered_props = {
                    k: v for k, v in pset_data.items() 
                    if not k.startswith('id') and k != 'type'
                }
                if filtered_props:
                    properties[pset_name] = filtered_props
                    
        except Exception as e:
            logger.debug(f"Could not extract properties: {e}")
        
        return properties
    
    def _get_building_elements(self) -> List[Any]:
        """Get all building elements from IFC file"""
        element_types = [
            "IfcWall", "IfcWallStandardCase",
            "IfcDoor", "IfcWindow",
            "IfcSlab", "IfcRoof",
            "IfcBeam", "IfcColumn",
            "IfcStair", "IfcRailing",
            "IfcCovering", "IfcCurtainWall",
            "IfcPlate", "IfcMember",
            "IfcBuildingElementProxy",
            "IfcSpace", "IfcZone"
        ]
        
        elements = []
        for elem_type in element_types:
            try:
                elements.extend(self.ifc_file.by_type(elem_type))
            except:
                pass  # Type not in schema or no elements
        
        return elements
    
    def get_classification_by_element_type(
        self,
        classifications: List[BSDDClassification]
    ) -> Dict[str, List[BSDDClassification]]:
        """Group classifications by IFC element type"""
        grouped = {}
        
        for classification in classifications:
            elem_type = classification.ifc_entity_type
            if elem_type not in grouped:
                grouped[elem_type] = []
            grouped[elem_type].append(classification)
        
        return grouped
    
    def get_classification_by_bsdd_code(
        self,
        classifications: List[BSDDClassification]
    ) -> Dict[str, List[BSDDClassification]]:
        """Group classifications by bSDD code"""
        grouped = {}
        
        for classification in classifications:
            code = classification.code
            if code not in grouped:
                grouped[code] = []
            grouped[code].append(classification)
        
        return grouped
    
    def filter_bsdd_only(
        self,
        classifications: List[BSDDClassification]
    ) -> List[BSDDClassification]:
        """Filter to only buildingSMART bSDD classifications"""
        return [
            c for c in classifications
            if "identifier.buildingsmart.org" in c.uri
        ]
    
    def get_statistics(
        self,
        result: IFCBSDDParseResult
    ) -> Dict[str, Any]:
        """Generate statistics about the parsed classifications"""
        stats = {
            "file_name": result.file_name,
            "ifc_schema": result.ifc_schema,
            "total_elements": result.total_elements,
            "classified_elements": result.classified_elements,
            "classification_coverage": (
                result.classified_elements / result.total_elements * 100
                if result.total_elements > 0 else 0
            ),
            "dictionaries_count": len(result.dictionaries_used),
            "dictionaries": list(result.dictionaries_used),
            "errors_count": len(result.errors),
            "warnings_count": len(result.warnings),
        }
        
        # Count by element type
        by_type = self.get_classification_by_element_type(result.classifications)
        stats["classifications_by_type"] = {
            elem_type: len(classifications)
            for elem_type, classifications in by_type.items()
        }
        
        # Count by bSDD code
        by_code = self.get_classification_by_bsdd_code(result.classifications)
        stats["classifications_by_code"] = {
            code: len(classifications)
            for code, classifications in by_code.items()
        }
        
        # bSDD vs non-bSDD
        bsdd_only = self.filter_bsdd_only(result.classifications)
        stats["bsdd_classifications"] = len(bsdd_only)
        stats["non_bsdd_classifications"] = len(result.classifications) - len(bsdd_only)
        
        return stats


def parse_ifc_for_bsdd(ifc_path: str) -> IFCBSDDParseResult:
    """
    Convenience function to parse an IFC file for bSDD classifications
    
    Args:
        ifc_path: Path to IFC file
        
    Returns:
        IFCBSDDParseResult with extracted classifications
    """
    parser = IFCBSDDParser()
    return parser.parse_file(ifc_path)
