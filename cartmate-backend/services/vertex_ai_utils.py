"""
Vertex AI Utilities - Environment-aware initialization for local and deployed environments
"""
import os
import logging
from typing import Optional
from google.oauth2 import service_account
import vertexai
from vertexai.preview.generative_models import GenerativeModel
from config.settings import settings

logger = logging.getLogger(__name__)

def initialize_vertex_ai(project_id: str = "imposing-kite-461508-v4", location: str = "us-central1") -> Optional[GenerativeModel]:
    """
    Initialize Vertex AI connection that works in both local and deployed environments.
    
    Args:
        project_id: Google Cloud project ID
        location: Vertex AI location
        
    Returns:
        GenerativeModel instance or None if initialization fails
    """
    try:
        # Determine the service account key path based on environment
        key_path = _get_service_account_key_path()
        
        if key_path and os.path.exists(key_path):
            # Use service account key file
            logger.info(f"Using service account key file: {key_path}")
            credentials = service_account.Credentials.from_service_account_file(key_path)
            vertexai.init(project=project_id, location=location, credentials=credentials)
        else:
            # Try to use default credentials (for deployed environments with workload identity)
            logger.info("Using default credentials (workload identity or gcloud auth)")
            vertexai.init(project=project_id, location=location)
        
        # Load the generative model
        model = GenerativeModel("gemini-2.5-flash")
        logger.info("Vertex AI initialized successfully")
        return model
        
    except Exception as e:
        logger.error(f"Error initializing Vertex AI: {e}")
        return None

def _get_service_account_key_path() -> Optional[str]:
    """
    Get the service account key path based on environment.
    
    Returns:
        Path to service account key file or None if not found
    """
    # Check if path is explicitly set in environment variables
    if settings.VERTEX_AI_SERVICE_ACCOUNT_KEY_PATH:
        return settings.VERTEX_AI_SERVICE_ACCOUNT_KEY_PATH
    
    # Check for deployment path first (for deployed environments)
    deployment_path = "/app/imposing-kite-461508-v4-71f861a0eecc.json"
    if os.path.exists(deployment_path):
        return deployment_path
    
    # Check for local development path
    local_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "imposing-kite-461508-v4-71f861a0eecc.json")
    if os.path.exists(local_path):
        return local_path
    
    # Check current working directory
    cwd_path = "imposing-kite-461508-v4-71f861a0eecc.json"
    if os.path.exists(cwd_path):
        return cwd_path
    
    logger.warning("No service account key file found, will try default credentials")
    return None
