"""
bSDD (buildingSMART Data Dictionary) API Client
Provides interface to query bSDD GraphQL and REST APIs for standardized building data
"""
import os
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


class BSDDEnvironment(Enum):
    """bSDD API environments"""
    PRODUCTION = "https://api.bsdd.buildingsmart.org"
    TEST = "https://test.bsdd.buildingsmart.org"


@dataclass
class BSDDDictionary:
    """Represents a bSDD Dictionary (formerly Domain)"""
    uri: str
    name: str
    version: str
    organization_code: str
    status: str
    language_code: str
    license: Optional[str] = None
    release_date: Optional[str] = None
    more_info_url: Optional[str] = None


@dataclass
class BSDDClass:
    """Represents a bSDD Class (formerly Classification)"""
    uri: str
    code: str
    name: str
    definition: Optional[str] = None
    class_type: Optional[str] = None
    related_ifc_entities: List[str] = None
    synonyms: List[str] = None
    properties: List[Dict] = None
    relations: List[Dict] = None
    parent_class_uri: Optional[str] = None
    
    def __post_init__(self):
        if self.related_ifc_entities is None:
            self.related_ifc_entities = []
        if self.synonyms is None:
            self.synonyms = []
        if self.properties is None:
            self.properties = []
        if self.relations is None:
            self.relations = []


@dataclass
class BSDDProperty:
    """Represents a bSDD Property"""
    uri: str
    code: str
    name: str
    definition: Optional[str] = None
    data_type: Optional[str] = None
    units: List[str] = None
    allowed_values: List[Dict] = None
    physical_quantity: Optional[str] = None
    dimension: Optional[str] = None
    
    def __post_init__(self):
        if self.units is None:
            self.units = []
        if self.allowed_values is None:
            self.allowed_values = []


class BSDDClient:
    """
    Client for interacting with buildingSMART Data Dictionary (bSDD) API
    Supports both REST and GraphQL endpoints
    """
    
    def __init__(
        self, 
        environment: BSDDEnvironment = BSDDEnvironment.PRODUCTION,
        auth_token: Optional[str] = None,
        user_agent: str = "BIMTwinOps/2.0.0"
    ):
        """
        Initialize bSDD client
        
        Args:
            environment: Production or test environment
            auth_token: Optional OAuth2 token for secured endpoints
            user_agent: User-Agent header for API requests
        """
        self.base_url = environment.value
        self.graphql_url = f"{self.base_url}/graphqls"  # Secured GraphQL endpoint
        self.auth_token = auth_token or os.getenv("BSDD_AUTH_TOKEN")
        self.session = requests.Session()
        
        # Add User-Agent header (required for REST APIs)
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json"
        })
        
        # Add Authorization header if token provided
        if self.auth_token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.auth_token}"
            })
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request to REST API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"bSDD API request failed: {e}")
            raise
    
    def _graphql_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute GraphQL query"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        try:
            response = self.session.post(
                self.graphql_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error(f"GraphQL errors: {data['errors']}")
                raise Exception(f"GraphQL query failed: {data['errors']}")
            
            return data.get("data", {})
        except requests.exceptions.RequestException as e:
            logger.error(f"bSDD GraphQL request failed: {e}")
            raise
    
    @lru_cache(maxsize=100)
    def get_dictionaries(
        self,
        include_test: bool = False,
        organization_code: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[BSDDDictionary]:
        """
        Get list of available dictionaries in bSDD using REST API
        
        Args:
            include_test: Include test dictionaries
            organization_code: Filter by organization code
            status: Filter by status (Active, Preview, Inactive)
        
        Returns:
            List of BSDDDictionary objects
        """
        endpoint = "/api/Dictionary/v1"
        params = {}
        
        if include_test:
            params["IncludeTestDictionaries"] = "true"
        if organization_code:
            params["OrganizationCode"] = organization_code
        if status:
            params["Status"] = status
        
        try:
            result = self._get(endpoint, params)
            dictionaries = result.get("dictionaries", [])
            
            return [
                BSDDDictionary(
                    uri=d.get("uri", ""),
                    name=d.get("name", ""),
                    version=d.get("version", ""),
                    organization_code=d.get("organizationCodeOwner", ""),
                    status=d.get("status", ""),
                    language_code=d.get("defaultLanguageCode", "en-GB"),
                    license=d.get("license"),
                    release_date=d.get("releaseDate"),
                    more_info_url=d.get("moreInfoUrl")
                )
                for d in dictionaries
            ]
        except Exception as e:
            logger.error(f"Failed to get dictionaries: {e}")
            return []
    
    def get_dictionary_classes(
        self,
        dictionary_uri: str,
        language_code: str = "en-GB",
        class_type: Optional[str] = None,
        related_ifc_entity: Optional[str] = None,
        include_properties: bool = True,
        fetch_all: bool = True
    ) -> List[BSDDClass]:
        """
        Get all classes from a dictionary using REST API with pagination support
        
        Args:
            dictionary_uri: URI of the dictionary
            language_code: Language code for results
            class_type: Filter by class type
            related_ifc_entity: Filter by IFC entity
            include_properties: Include class properties
            fetch_all: Fetch all results using pagination (may take time for large dictionaries)
            
        Returns:
            List of BSDDClass objects
        """
        endpoint = "/api/Dictionary/v1/Classes"
        all_classes = []
        offset = 0
        limit = 1000  # Max allowed by API
        
        while True:
            params = {
                "Uri": dictionary_uri,
                "LanguageCode": language_code,
                "Offset": offset,
                "Limit": limit
            }
            
            if class_type:
                params["ClassType"] = class_type
            if related_ifc_entity:
                params["RelatedIfcEntities"] = related_ifc_entity
            
            try:
                result = self._get(endpoint, params)
                classes = result.get("classes", [])
                
                if not classes:
                    break
                
                all_classes.extend([
                    BSDDClass(
                        uri=c.get("uri", ""),
                        code=c.get("code", ""),
                        name=c.get("name", ""),
                        definition=c.get("definition"),
                        class_type=c.get("classType"),
                        related_ifc_entities=c.get("relatedIfcEntityNames", []),
                        synonyms=c.get("synonyms", []),
                        properties=c.get("classProperties", []) if include_properties else []
                    )
                    for c in classes
                ])
                
                logger.info(f"Fetched {len(all_classes)} classes so far from {dictionary_uri}")
                
                # If we got less than limit, we've reached the end
                if len(classes) < limit or not fetch_all:
                    break
                
                offset += limit
                
            except Exception as e:
                logger.error(f"Failed to get classes for dictionary {dictionary_uri} at offset {offset}: {e}")
                if all_classes:
                    logger.warning(f"Returning {len(all_classes)} classes fetched before error")
                    break
                else:
                    return []
        
        logger.info(f"Total classes fetched: {len(all_classes)}")
        return all_classes
    
    def get_dictionary_properties(
        self,
        dictionary_uri: str,
        language_code: str = "en-GB",
        fetch_all: bool = True
    ) -> List[BSDDProperty]:
        """
        Get all properties from a dictionary using REST API with pagination support
        
        Args:
            dictionary_uri: URI of the dictionary
            language_code: Language code for results
            fetch_all: Fetch all results using pagination
            
        Returns:
            List of BSDDProperty objects
        """
        endpoint = "/api/Dictionary/v1/Properties"
        all_properties = []
        offset = 0
        limit = 1000  # Max allowed by API
        
        while True:
            params = {
                "Uri": dictionary_uri,
                "LanguageCode": language_code,
                "Offset": offset,
                "Limit": limit
            }
            
            try:
                result = self._get(endpoint, params)
                properties = result.get("properties", [])
                
                if not properties:
                    break
                
                all_properties.extend([
                    BSDDProperty(
                        uri=p.get("uri", ""),
                        code=p.get("code", ""),
                        name=p.get("name", ""),
                        definition=p.get("definition"),
                        data_type=p.get("dataType"),
                        units=p.get("units", []),
                        allowed_values=p.get("allowedValues", []),
                        physical_quantity=p.get("physicalQuantity"),
                        dimension=p.get("dimension")
                    )
                    for p in properties
                ])
                
                logger.info(f"Fetched {len(all_properties)} properties so far from {dictionary_uri}")
                
                # If we got less than limit, we've reached the end
                if len(properties) < limit or not fetch_all:
                    break
                
                offset += limit
                
            except Exception as e:
                logger.error(f"Failed to get properties for dictionary {dictionary_uri} at offset {offset}: {e}")
                if all_properties:
                    logger.warning(f"Returning {len(all_properties)} properties fetched before error")
                    break
                else:
                    return []
        
        logger.info(f"Total properties fetched: {len(all_properties)}")
        return all_properties
    
    def search_classes(
        self,
        dictionary_uri: str,
        search_text: Optional[str] = None,
        related_ifc_entity: Optional[str] = None,
        language_code: str = "en-GB"
    ) -> List[BSDDClass]:
        """
        Search for classes in a dictionary using REST API
        
        Args:
            dictionary_uri: URI of the dictionary to search in
            search_text: Optional text to search for
            related_ifc_entity: Optional IFC entity name to filter by
            language_code: Language code for results
            
        Returns:
            List of BSDDClass objects
        """
        endpoint = "/api/Dictionary/v1/Classes"
        params = {
            "Uri": dictionary_uri,
            "LanguageCode": language_code
        }
        
        if search_text:
            params["SearchText"] = search_text
        if related_ifc_entity:
            params["RelatedIfcEntities"] = related_ifc_entity
        
        try:
            result = self._get(endpoint, params)
            classes = result.get("classes", [])
            
            return [
                BSDDClass(
                    uri=c.get("uri", ""),
                    code=c.get("code", ""),
                    name=c.get("name", ""),
                    definition=c.get("definition"),
                    class_type=c.get("classType"),
                    related_ifc_entities=c.get("relatedIfcEntityNames", []),
                    synonyms=c.get("synonyms", [])
                )
                for c in classes
            ]
        except Exception as e:
            logger.error(f"Failed to search classes in {dictionary_uri}: {e}")
            return []
    
    def get_class_details(
        self,
        dictionary_uri: str,
        class_uri: str,
        include_properties: bool = True,
        include_relations: bool = True,
        include_children: bool = False,
        language_code: str = "en-GB"
    ) -> BSDDClass:
        """
        Get detailed information about a class using REST API
        
        Args:
            dictionary_uri: URI of the dictionary
            class_uri: URI of the class
            include_properties: Include class properties
            include_relations: Include class relations
            include_children: Include child classes
            language_code: Language code for results
            
        Returns:
            BSDDClass object with full details
        """
        endpoint = "/api/Class/v1"
        params = {
            "Uri": class_uri,
            "LanguageCode": language_code,
            "IncludeClassProperties": str(include_properties).lower(),
            "IncludeClassRelations": str(include_relations).lower(),
            "IncludeChilds": str(include_children).lower()
        }
        
        try:
            result = self._get(endpoint, params)
            
            if not result:
                raise ValueError(f"Class not found: {class_uri}")
            
            parent_ref = result.get("parentClassReference")
            parent_uri = parent_ref.get("uri") if parent_ref else None
            
            return BSDDClass(
                uri=result.get("uri", ""),
                code=result.get("code", ""),
                name=result.get("name", ""),
                definition=result.get("definition"),
                class_type=result.get("classType"),
                related_ifc_entities=result.get("relatedIfcEntityNames", []),
                synonyms=result.get("synonyms", []),
                properties=result.get("classProperties", []) if include_properties else [],
                relations=result.get("classRelations", []) if include_relations else [],
                parent_class_uri=parent_uri
            )
        except Exception as e:
            logger.error(f"Failed to get class details for {class_uri}: {e}")
            raise
    
    def get_properties_for_class(
        self,
        dictionary_uri: str,
        class_uri: str
    ) -> List[BSDDProperty]:
        """
        Get all properties defined for a class
        
        Args:
            dictionary_uri: URI of the dictionary
            class_uri: URI of the class
            
        Returns:
            List of BSDDProperty objects
        """
        class_details = self.get_class_details(
            dictionary_uri,
            class_uri,
            include_properties=True,
            include_relations=False
        )
        
        return [
            BSDDProperty(
                uri=p.get("uri", ""),
                code=p.get("code", ""),
                name=p.get("name", ""),
                definition=p.get("definition") or p.get("description"),
                data_type=p.get("dataType"),
                units=p.get("units", []),
                allowed_values=p.get("allowedValues", []),
                physical_quantity=p.get("physicalQuantity"),
                dimension=p.get("dimension")
            )
            for p in class_details.properties
        ]
    
    def get_ifc_mappings(
        self,
        ifc_entity: str,
        dictionary_uri: Optional[str] = None
    ) -> List[BSDDClass]:
        """
        Find bSDD classes mapped to an IFC entity
        
        Args:
            ifc_entity: IFC entity name (e.g., "IfcWall")
            dictionary_uri: Optional specific dictionary to search
            
        Returns:
            List of BSDDClass objects mapped to the IFC entity
        """
        # Use REST API endpoint for IFC mapping search
        endpoint = "/api/Dictionary/v1/Classes"
        params = {
            "RelatedIfcEntities": ifc_entity
        }
        
        if dictionary_uri:
            params["Uri"] = dictionary_uri
        
        try:
            result = self._get(endpoint, params)
            classes = result.get("classes", [])
            
            return [
                BSDDClass(
                    uri=c.get("uri", ""),
                    code=c.get("code", ""),
                    name=c.get("name", ""),
                    definition=c.get("definition"),
                    class_type=c.get("classType"),
                    related_ifc_entities=c.get("relatedIfcEntityNames", [])
                )
                for c in classes
            ]
        except Exception as e:
            logger.error(f"Failed to get IFC mappings for {ifc_entity}: {e}")
            return []
    
    def text_search(
        self,
        search_text: str,
        language_code: str = "en-GB",
        dictionary_uris: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform text search across dictionaries
        
        Args:
            search_text: Text to search for
            language_code: Language code
            dictionary_uris: Optional list of dictionary URIs to search in
            
        Returns:
            Search results grouped by dictionary
        """
        endpoint = "/api/TextSearch/v2"
        params = {
            "SearchText": search_text,
            "LanguageCode": language_code
        }
        
        if dictionary_uris:
            params["DictionaryUris"] = ",".join(dictionary_uris)
        
        return self._get(endpoint, params)


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize client
    client = BSDDClient(environment=BSDDEnvironment.PRODUCTION)
    
    # Get available dictionaries
    print("\n=== Available Dictionaries ===")
    dictionaries = client.get_dictionaries()
    for d in dictionaries[:5]:  # Show first 5
        print(f"{d.name} ({d.version}) - {d.uri}")
    
    # Search for IFC dictionary
    ifc_dicts = [d for d in dictionaries if "ifc" in d.name.lower()]
    if ifc_dicts:
        ifc_dict = ifc_dicts[0]
        print(f"\n=== Searching in {ifc_dict.name} ===")
        
        # Search for wall classes
        classes = client.search_classes(
            ifc_dict.uri,
            search_text="wall"
        )
        print(f"Found {len(classes)} wall-related classes")
        
        if classes:
            # Get details for first class
            first_class = classes[0]
            print(f"\n=== Details for {first_class.name} ===")
            detailed_class = client.get_class_details(
                ifc_dict.uri,
                first_class.uri
            )
            print(f"Properties: {len(detailed_class.properties)}")
            print(f"Relations: {len(detailed_class.relations)}")
            print(f"IFC Entities: {', '.join(detailed_class.related_ifc_entities)}")
    
    # Find bSDD mappings for IfcWall
    print("\n=== bSDD Classes mapped to IfcWall ===")
    wall_mappings = client.get_ifc_mappings("IfcWall")
    for mapping in wall_mappings[:5]:  # Show first 5
        print(f"{mapping.name} ({mapping.code}) - {mapping.uri}")
