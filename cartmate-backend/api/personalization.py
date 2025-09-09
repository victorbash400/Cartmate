"""
Personalization API endpoints for handling user style preferences and image analysis
"""
import logging
import base64
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import vertexai
from vertexai.preview.generative_models import GenerativeModel
from google.oauth2 import service_account
from services.storage.redis_client import redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/personalization", tags=["personalization"])

class PersonalizationData(BaseModel):
    session_id: str
    style_preferences: Optional[str] = None
    budget_range: Optional[Dict[str, int]] = None
    image_analysis: Optional[Dict[str, Any]] = None

class PersonalizationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class StyleAnalyzer:
    """Simple style analyzer using Vertex AI Vision"""
    
    def __init__(self):
        self.model = None
        self._initialize_vertex_ai()
    
    def _initialize_vertex_ai(self):
        """Initialize Vertex AI for image analysis"""
        try:
            project_id = "imposing-kite-461508-v4"
            location = "us-central1"
            key_path = "C:\\Users\\Victo\\Desktop\\CartMate\\cartmate-backend\\imposing-kite-461508-v4-71f861a0eecc.json"
            
            credentials = service_account.Credentials.from_service_account_file(key_path)
            vertexai.init(project=project_id, location=location, credentials=credentials)
            
            self.model = GenerativeModel("gemini-2.5-flash")
            logger.info("Vertex AI initialized successfully for StyleAnalyzer")
        except Exception as e:
            logger.error(f"Error initializing Vertex AI for StyleAnalyzer: {e}")
            self.model = None
    
    async def analyze_style_image(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze uploaded image for style characteristics"""
        if not self.model:
            raise HTTPException(status_code=500, detail="Style analysis service unavailable")
        
        try:
            # Convert image to base64 for Vertex AI
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            analysis_prompt = """
            Analyze this image for fashion and style characteristics. Focus on:
            1. Clothing style (casual, formal, bohemian, minimalist, etc.)
            2. Color palette (dominant colors, color scheme)
            3. Fashion categories (streetwear, business, vintage, etc.)
            4. Overall aesthetic (modern, classic, trendy, etc.)
            
            Respond with a JSON object containing:
            {
                "style": "primary style category",
                "colors": ["color1", "color2", "color3"],
                "categories": ["category1", "category2"],
                "aesthetic": "overall aesthetic",
                "confidence": 0.0-1.0
            }
            """
            
            # Create the image part for the model
            import vertexai.preview.generative_models as generative_models
            
            image_part = generative_models.Part.from_data(
                data=image_data,
                mime_type="image/jpeg"
            )
            
            response = self.model.generate_content([image_part, analysis_prompt])
            
            # Parse the response
            response_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            
            analysis_result = json.loads(response_text)
            logger.info(f"Style analysis completed: {analysis_result}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing style image: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to analyze image: {str(e)}")

# Global style analyzer instance
style_analyzer = StyleAnalyzer()

@router.post("/save", response_model=PersonalizationResponse)
async def save_personalization_data(
    session_id: str = Form(...),
    style_preferences: Optional[str] = Form(None),
    budget_min: Optional[int] = Form(None),
    budget_max: Optional[int] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    """Save personalization data for a session"""
    try:
        logger.info(f"Saving personalization data for session {session_id}")
        
        # Prepare personalization data
        personalization_data = {
            "session_id": session_id,
            "style_preferences": style_preferences,
            "budget_range": None,
            "image_analysis": None
        }
        
        # Handle budget range
        if budget_min is not None and budget_max is not None:
            personalization_data["budget_range"] = {
                "min": budget_min,
                "max": budget_max
            }
        
        # Handle image analysis
        if image and image.content_type.startswith('image/'):
            logger.info(f"Processing uploaded image: {image.filename}")
            image_data = await image.read()
            
            # Analyze the image for style characteristics
            try:
                analysis_result = await style_analyzer.analyze_style_image(image_data)
                personalization_data["image_analysis"] = analysis_result
                logger.info(f"Image analysis completed for session {session_id}")
            except Exception as e:
                logger.warning(f"Image analysis failed for session {session_id}: {e}")
                # Continue without image analysis
        
        # Store in Redis
        key = f"personalization:{session_id}"
        await redis_client.set(key, json.dumps(personalization_data), expire=86400)  # 24 hours
        
        logger.info(f"Personalization data saved for session {session_id}")
        
        return PersonalizationResponse(
            success=True,
            message="Personalization data saved successfully",
            data=personalization_data
        )
        
    except Exception as e:
        logger.error(f"Error saving personalization data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save personalization data: {str(e)}")

@router.get("/get/{session_id}", response_model=PersonalizationResponse)
async def get_personalization_data(session_id: str):
    """Get personalization data for a session"""
    try:
        key = f"personalization:{session_id}"
        data = await redis_client.get(key)
        
        if not data:
            return PersonalizationResponse(
                success=False,
                message="No personalization data found for this session"
            )
        
        personalization_data = json.loads(data)
        
        return PersonalizationResponse(
            success=True,
            message="Personalization data retrieved successfully",
            data=personalization_data
        )
        
    except Exception as e:
        logger.error(f"Error retrieving personalization data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve personalization data: {str(e)}")

@router.delete("/clear/{session_id}", response_model=PersonalizationResponse)
async def clear_personalization_data(session_id: str):
    """Clear personalization data for a session"""
    try:
        key = f"personalization:{session_id}"
        await redis_client.delete(key)
        
        return PersonalizationResponse(
            success=True,
            message="Personalization data cleared successfully"
        )
        
    except Exception as e:
        logger.error(f"Error clearing personalization data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear personalization data: {str(e)}")
