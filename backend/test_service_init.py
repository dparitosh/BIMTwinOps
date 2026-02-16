"""
Test if PointCloudSemanticService can be initialized properly
"""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    logger.info("Importing pointcloud_semantic module...")
    from api.pointcloud_semantic import get_service, PointCloudSemanticService
    
    logger.info("Getting service instance...")
    service = get_service()
    
    logger.info(f"Service initialized successfully!")
    logger.info(f"Semantic mappings loaded: {len(service.semantic_mappings)}")
    logger.info(f"Neo4j driver: {service.kg.driver is not None}")
    
    # Test the router
    from api.pointcloud_semantic import router
    logger.info(f"Router prefix: {router.prefix}")
    logger.info(f"Router tags: {router.tags}")
    logger.info(f"Number of routes: {len(router.routes)}")
    for route in router.routes:
        logger.info(f"  - {route.methods} {route.path}")
    
except Exception as e:
    logger.error(f"Failed to initialize service: {e}", exc_info=True)
    sys.exit(1)
