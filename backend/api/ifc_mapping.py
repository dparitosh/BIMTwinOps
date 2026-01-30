# Validation utility for bSDD URI referencing
import re

def validate_bsdd_uri(uri: str) -> bool:
    """
    Validate that a URI matches the expected bSDD URI format.
    Example: http://identifier.buildingsmart.org/uri/{organization}/{dictionary}/{version}/class/{code}
    """
    pattern = r"^https?://identifier\.buildingsmart\.org/uri/[\w-]+/[\w-]+/[\w.-]+/(class|property|material)/[\w-]+$"
    return bool(re.match(pattern, uri))

def validate_ifc_ids_references(entities: list) -> dict:
    """
    Validate a list of IFC/IDS entities for correct bSDD referencing.
    Returns a dict with errors and compliance status.
    """
    errors = []
    for idx, entity in enumerate(entities):
        uri = entity.get("uri")
        if not uri:
            errors.append({"index": idx, "error": "Missing URI"})
        elif not validate_bsdd_uri(uri):
            errors.append({"index": idx, "uri": uri, "error": "Invalid bSDD URI format"})
    return {
        "total": len(entities),
        "errors": errors,
        "compliant": len(errors) == 0
    }
def get_bsdd_dictionary_uri(organization_code: str, dictionary_code: str, version: str) -> str:
    """
    Generate IDS-compliant URI for a bSDD dictionary.
    """
    return f"http://identifier.buildingsmart.org/uri/{organization_code}/{dictionary_code}/{version}/"

def get_bsdd_class_uri(organization_code: str, dictionary_code: str, version: str, class_code: str) -> str:
    """
    Generate IDS-compliant URI for a bSDD class.
    """
    return f"http://identifier.buildingsmart.org/uri/{organization_code}/{dictionary_code}/{version}/class/{class_code}"

def get_bsdd_property_uri(organization_code: str, dictionary_code: str, version: str, property_code: str) -> str:
    """
    Generate IDS-compliant URI for a bSDD property.
    """
    return f"http://identifier.buildingsmart.org/uri/{organization_code}/{dictionary_code}/{version}/prop/{property_code}"

def get_bsdd_material_uri(organization_code: str, dictionary_code: str, version: str, material_code: str) -> str:
    """
    Generate IDS-compliant URI for a bSDD material.
    """
    return f"http://identifier.buildingsmart.org/uri/{organization_code}/{dictionary_code}/{version}/class/{material_code}"
"""
IFC Mapping Utilities for bSDD Entities
Provides functions to map bSDD dictionary, class, property, and material to IFC/IDS-compliant objects.
"""

def map_bsdd_dictionary_to_ifc_classification(bsdd_dict: dict) -> dict:
    """
    Map a bSDD dictionary to an IFC IfcClassification entity.
    """
    required = ["name", "uri", "version", "organization_code", "release_date"]
    missing = [field for field in required if not bsdd_dict.get(field)]
    if missing:
        return {"error": f"Missing required fields: {', '.join(missing)}"}
    return {
        "IfcClassification": {
            "Name": bsdd_dict["name"],
            "Specification": bsdd_dict["uri"],
            "Edition": bsdd_dict["version"],
            "Source": bsdd_dict["organization_code"],
            "EditionDate": bsdd_dict["release_date"],
            "Location": bsdd_dict["uri"],
        }
    }

def map_bsdd_class_to_ifc_classification_reference(bsdd_class: dict) -> dict:
    """
    Map a bSDD class to an IFC IfcClassificationReference entity.
    """
    required = ["name", "code", "uri"]
    missing = [field for field in required if not bsdd_class.get(field)]
    if missing:
        return {"error": f"Missing required fields: {', '.join(missing)}"}
    return {
        "IfcClassificationReference": {
            "Name": bsdd_class["name"],
            "Identification": bsdd_class["code"],
            "Location": bsdd_class["uri"],
        }
    }

def map_bsdd_property_to_ifc_property_single_value(bsdd_property: dict) -> dict:
    """
    Map a bSDD property to an IFC IfcPropertySingleValue entity.
    """
    required = ["code", "uri"]
    missing = [field for field in required if not bsdd_property.get(field)]
    if missing:
        return {"error": f"Missing required fields: {', '.join(missing)}"}
    return {
        "IfcPropertySingleValue": {
            "Name": bsdd_property["code"],
            "Description": bsdd_property["uri"],
            "NominalValue": bsdd_property.get("predefined_value"),
            "Unit": bsdd_property.get("unit"),
            "EnumerationValues": bsdd_property.get("allowed_values", []),
        }
    }

def map_bsdd_material_to_ifc_material(bsdd_material: dict) -> dict:
    """
    Map a bSDD material to IFC IfcMaterial and IfcClassificationReference entities.
    """
    required = ["name", "code", "uri"]
    missing = [field for field in required if not bsdd_material.get(field)]
    if missing:
        return {"error": f"Missing required fields: {', '.join(missing)}"}
    return {
        "IfcMaterial": {
            "Name": bsdd_material["name"],
        },
        "IfcClassificationReference": {
            "Name": bsdd_material["name"],
            "Identification": bsdd_material["code"],
            "Location": bsdd_material["uri"],
        }
    }
