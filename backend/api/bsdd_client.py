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
        auth_token: Optional[str] = None
    ):
        """
        Initialize bSDD client
        
        Args:
            environment: Production or test environment
            auth_token: Optional OAuth2 token for secured endpoints
        """
        self.base_url = environment.value
        self.graphql_url = f"{self.base_url}/graphql"
        self.auth_token = auth_token or os.getenv("BSDD_AUTH_TOKEN")
        self.session = requests.Session()
        
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
    def get_dictionaries(self) -> List[BSDDDictionary]:
        """
        Get list of available dictionaries in bSDD
        
        Returns:
            List of BSDDDictionary objects
        """
        query = """
        {
          dictionaries {
            uri
            name
            version
            organizationCodeOwner
            status
            languageCode
            license
            releaseDate
            moreInfoUrl
          }
        }
        """
        
        result = self._graphql_query(query)
        dictionaries = result.get("dictionaries", [])
        
        return [
            BSDDDictionary(
                uri=d["uri"],
                name=d["name"],
                version=d["version"],
                organization_code=d.get("organizationCodeOwner", ""),
                status=d["status"],
                language_code=d["languageCode"],
                license=d.get("license"),
                release_date=d.get("releaseDate"),
                more_info_url=d.get("moreInfoUrl")
            )
            for d in dictionaries
        ]
    
    def search_classes(
        self,
        dictionary_uri: str,
        search_text: Optional[str] = None,
        related_ifc_entity: Optional[str] = None,
        language_code: str = "en-GB"
    ) -> List[BSDDClass]:
        """
        Search for classes in a dictionary
        
        Args:
            dictionary_uri: URI of the dictionary to search in
            search_text: Optional text to search for
            related_ifc_entity: Optional IFC entity name to filter by
            language_code: Language code for results
            
        Returns:
            List of BSDDClass objects
        """
        query = """
        query ($dictionaryUri: String!, $searchText: String, $languageCode: String) {
          dictionary(uri: $dictionaryUri) {
            classSearch(searchText: $searchText, languageCode: $languageCode) {
              uri
              code
              name
              definition
              classType
              synonyms
              relatedIfcEntityNames
            }
          }
        }
        """
        
        variables = {
            "dictionaryUri": dictionary_uri,
            "searchText": search_text,
            "languageCode": language_code
        }
        
        result = self._graphql_query(query, variables)
        classes = result.get("dictionary", {}).get("classSearch", [])
        
        # Filter by IFC entity if specified
        if related_ifc_entity:
            classes = [
                c for c in classes
                if related_ifc_entity in c.get("relatedIfcEntityNames", [])
            ]
        
        return [
            BSDDClass(
                uri=c["uri"],
                code=c["code"],
                name=c["name"],
                definition=c.get("definition"),
                class_type=c.get("classType"),
                related_ifc_entities=c.get("relatedIfcEntityNames", []),
                synonyms=c.get("synonyms", [])
            )
            for c in classes
        ]
    
    def get_class_details(
        self,
        dictionary_uri: str,
        class_uri: str,
        include_properties: bool = True,
        include_relations: bool = True,
        include_children: bool = False
    ) -> BSDDClass:
        """
        Get detailed information about a class including properties and relations
        
        Args:
            dictionary_uri: URI of the dictionary
            class_uri: URI of the class
            include_properties: Include class properties
            include_relations: Include class relations
            include_children: Include child classes
            
        Returns:
            BSDDClass object with full details
        """
        query = """
        query ($dictionaryUri: String!, $classUri: String!, $includeChildren: Boolean!) {
          dictionary(uri: $dictionaryUri) {
            class(uri: $classUri, includeChildren: $includeChildren) {
              uri
              code
              name
              definition
              classType
              synonyms
              relatedIfcEntityNames
              parentClassReference {
                uri
                name
              }
              properties {
                code
                name
                uri
                description
                definition
                dataType
                isRequired
                pattern
                dimension
                physicalQuantity
                allowedValues {
                  code
                  value
                }
                units
              }
              relations {
                relatedClassName
                relatedClassUri
                relationType
              }
              childs {
                uri
                name
                code
              }
            }
          }
        }
        """
        
        variables = {
            "dictionaryUri": dictionary_uri,
            "classUri": class_uri,
            "includeChildren": include_children
        }
        
        result = self._graphql_query(query, variables)
        class_data = result.get("dictionary", {}).get("class", {})
        
        if not class_data:
            raise ValueError(f"Class not found: {class_uri}")
        
        parent_ref = class_data.get("parentClassReference")
        parent_uri = parent_ref.get("uri") if parent_ref else None
        
        return BSDDClass(
            uri=class_data["uri"],
            code=class_data["code"],
            name=class_data["name"],
            definition=class_data.get("definition"),
            class_type=class_data.get("classType"),
            related_ifc_entities=class_data.get("relatedIfcEntityNames", []),
            synonyms=class_data.get("synonyms", []),
            properties=class_data.get("properties", []) if include_properties else [],
            relations=class_data.get("relations", []) if include_relations else [],
            parent_class_uri=parent_uri
        )
    
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
