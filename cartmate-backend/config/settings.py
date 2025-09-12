from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "CartMate"
    
    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # gRPC Services
    PRODUCT_CATALOG_SERVICE_HOST: str = "localhost"
    PRODUCT_CATALOG_SERVICE_PORT: int = 3550
    
    CART_SERVICE_HOST: str = "localhost"
    CART_SERVICE_PORT: int = 50052
    
    CHECKOUT_SERVICE_HOST: str = "localhost"
    CHECKOUT_SERVICE_PORT: int = 5050
    
    PAYMENT_SERVICE_HOST: str = "localhost"
    PAYMENT_SERVICE_PORT: int = 50051
    
    AD_SERVICE_HOST: str = "localhost"
    AD_SERVICE_PORT: int = 9555
    
    # Vertex AI Settings
    VERTEX_AI_PROJECT_ID: Optional[str] = None
    VERTEX_AI_LOCATION: str = "us-central1"
    
    # Perplexity API
    PERPLEXITY_API_KEY: Optional[str] = None
    SONAR_API_KEY: Optional[str] = None
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create settings instance
settings = Settings()
