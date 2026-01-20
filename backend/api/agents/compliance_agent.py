import re

class ComplianceAgent:
        def suggest_fixes(self, entity: dict) -> dict:
            """
            Use GenAI (LLM) to suggest automated fixes for non-compliant IFC entity data.
            This is a placeholder for LLM integration; in production, connect to an LLM service.
            """
            # Example: Suggest a valid URI if missing/invalid, or recommend adding missing associations
            suggestions = []
            if not entity.get("uri"):
                suggestions.append("Add a valid bSDD URI for this entity.")
            elif not self._is_valid_bsdd_uri(entity["uri"]):
                suggestions.append("Correct the bSDD URI format to match the standard.")
            for field in ["classification", "property", "material"]:
                if field in entity and not entity[field]:
                    suggestions.append(f"Add or correct the {field} association.")
            if not suggestions:
                suggestions.append("No issues detected. Entity is compliant.")
            return {"entity": entity.get("name", "Unknown"), "suggestions": suggestions}
    """
    Agent for validating IFC models against bSDD standards.
    Checks classification, property, and material associations for compliance.
    """
    def __init__(self):
        pass

    def validate_entity(self, entity: dict) -> dict:
        """
        Validate a single IFC entity for bSDD compliance and provide detailed reporting.
        """
        errors = []
        report = {}
        uri = entity.get("uri")
        if not uri:
            errors.append("Missing bSDD URI")
            report["uri"] = "Missing"
        elif not self._is_valid_bsdd_uri(uri):
            errors.append(f"Invalid bSDD URI: {uri}")
            report["uri"] = "Invalid"
        else:
            report["uri"] = "Valid"
        # Check required classification/property/material fields
        for field in ["classification", "property", "material"]:
            if field in entity:
                if not entity[field]:
                    errors.append(f"Missing {field} association")
                    report[field] = "Missing"
                else:
                    report[field] = "Present"
            else:
                report[field] = "Not Provided"
        return {
            "entity": entity.get("name", "Unknown"),
            "errors": errors,
            "compliant": len(errors) == 0,
            "report": report
        }

    def validate_entities(self, entities: list) -> dict:
        """
        Validate a list of IFC entities for bSDD compliance.
        """
        results = [self.validate_entity(e) for e in entities]
        non_compliant = [r for r in results if not r["compliant"]]
        return {
            "total": len(entities),
            "non_compliant": len(non_compliant),
            "results": results
        }

    def _is_valid_bsdd_uri(self, uri: str) -> bool:
        pattern = r"^https?://identifier\.buildingsmart\.org/uri/[\w-]+/[\w-]+/[\w.-]+/(class|property|material)/[\w-]+$"
        return bool(re.match(pattern, uri))
