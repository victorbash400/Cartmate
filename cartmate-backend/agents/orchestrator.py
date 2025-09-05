import logging
import os
from google.cloud import aiplatform
from google.oauth2 import service_account
import vertexai
from vertexai.preview.generative_models import GenerativeModel, ChatSession

class OrchestratorAgent:
    """
    The primary agent responsible for managing the conversation with the user.
    It uses Vertex AI to generate responses.
    """
    def __init__(self):
        self.chat_model = None
        self.chat_session = None
        try:
            # Configure the project and location
            project_id = "imposing-kite-461508-v4"
            location = "us-central1"
            
            # Path to your service account key file
            key_path = "C:\\Users\\Victo\\Desktop\\CartMate\\cartmate-backend\\imposing-kite-461508-v4-71f861a0eecc.json"
            
            # Authenticate using the service account key
            credentials = service_account.Credentials.from_service_account_file(key_path)
            
            # Initialize Vertex AI
            vertexai.init(project=project_id, location=location, credentials=credentials)
            
            # Load the generative model
            # Use the correct current model name - Gemini 2.5 Flash for best price-performance
            # Alternative options: "gemini-2.5-pro" for advanced reasoning, "gemini-2.0-flash" for older version
            self.chat_model = GenerativeModel("gemini-2.5-flash")
            self.chat_session = self.chat_model.start_chat()
            
            logging.info("Vertex AI initialized successfully.")

        except Exception as e:
            logging.error(f"Error initializing Vertex AI: {e}")
            # You might want to handle this more gracefully
            raise

    async def handle_message(self, message: str) -> str:
        """
        Processes a user's message using Vertex AI and returns a response.
        """
        if not self.chat_session:
            return "Error: Chat session not initialized."

        try:
            logging.info(f"Sending message to Vertex AI: {message}")
            response = self.chat_session.send_message(message)
            return response.text
        except Exception as e:
            logging.error(f"Error communicating with Vertex AI: {e}")
            return "Sorry, I'm having trouble connecting to the AI service."

# Create a single instance of the agent
orchestrator_agent = OrchestratorAgent()