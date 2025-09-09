import logging
import asyncio
from typing import List, Dict, Any
from services.boutique.product_catalog_client import product_catalog_client
from agents.base import BaseAgent
from models.a2a import A2AMessage, A2ARequest, A2AResponse, A2AMessageType, A2ARequestType, A2AFrontendNotification
from google.protobuf.json_format import MessageToDict

# Vertex AI imports
import vertexai
from vertexai.preview.generative_models import GenerativeModel
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

class ProductDiscoveryAgent(BaseAgent):
    """
    Intelligent AI-powered product discovery agent that uses Vertex AI to understand
    user queries and provide smart product recommendations.
    """
    
    def __init__(self):
        super().__init__("product_discovery_001", "product_discovery")
        self.registration.capabilities = [
            "search_products", 
            "get_product_details", 
            "intelligent_product_matching",
            "category_filtering",
            "product_recommendations"
        ]
        
        # Initialize Vertex AI for intelligent product analysis
        self.ai_model = None
        self._initialize_vertex_ai()
        
        # Product categories and keywords mapping
        self.category_keywords = {
            "clothing": ["shirt", "pants", "dress", "hoodie", "jacket", "sweater", "top", "bottom"],
            "footwear": ["shoes", "boots", "sneakers", "sandals", "heels", "flats"],
            "accessories": ["bag", "wallet", "belt", "watch", "jewelry", "hat", "cap"],
            "home": ["mug", "cup", "jar", "decor", "kitchen", "storage"],
            "tech": ["camera", "lens", "electronics", "gadget"],
            "outdoor": ["backpack", "travel", "sports"]
        }
    
    def _initialize_vertex_ai(self):
        """Initialize Vertex AI for intelligent product analysis"""
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
            self.ai_model = GenerativeModel("gemini-2.5-flash")
            
            logger.info("Vertex AI initialized successfully for ProductDiscoveryAgent")
        except Exception as e:
            logger.error(f"Error initializing Vertex AI for ProductDiscoveryAgent: {e}")
            self.ai_model = None

    async def start(self):
        """Start the product discovery agent"""
        await super().start()
        logger.info("Product Discovery Agent started")

    async def handle_message(self, message: A2AMessage) -> bool:
        """
        Handle incoming A2A messages.
        """
        try:
            if message.type == A2AMessageType.REQUEST:
                # The message should now be properly deserialized as A2ARequest
                if isinstance(message, A2ARequest):
                    return await self.handle_request(message)
                else:
                    logger.error(f"Received REQUEST message but it's not an A2ARequest: {type(message)}")
                    return False
            else:
                logger.info(f"ProductDiscoveryAgent received {message.type} message: {message.content}")
                return True
        except Exception as e:
            logger.error(f"Error handling message in ProductDiscoveryAgent: {e}")
            return False

    async def handle_request(self, request: A2ARequest) -> bool:
        """
        Handle incoming requests from other agents.
        """
        logger.info(f"ProductDiscoveryAgent received request: {request.request_type}")
        
        try:
            if request.request_type == A2ARequestType.SEARCH_PRODUCTS:
                query = request.content.get("query", "")
                logger.info(f"Searching for products: {query}")
                
                # Send notification that we're processing the request
                notification = A2AFrontendNotification(
                    sender=self.agent_id,
                    receiver=request.sender,
                    notification_type="agent_thinking",
                    agent_name="Product Discovery Agent",
                    agent_id=self.agent_id,
                    content=f"Searching for products matching '{query}'"
                )
                await self.send_message(request.sender, notification)
                
                # Perform intelligent product search
                products = await self._intelligent_product_search(query)
                logger.info(f"Found {len(products)} products after intelligent filtering.")
                
                # Send notification about completion
                completion_notification = A2AFrontendNotification(
                    sender=self.agent_id,
                    receiver=request.sender,
                    notification_type="agent_action",
                    agent_name="Product Discovery Agent",
                    agent_id=self.agent_id,
                    content=f"Found {len(products)} products for '{query}'"
                )
                await self.send_message(request.sender, completion_notification)
                
                # Convert protobuf objects to dictionaries (handle both real protobuf and mock data)
                product_dicts = []
                for p in products:
                    if hasattr(p, 'DESCRIPTOR'):
                        # Real protobuf object
                        product_dicts.append(MessageToDict(p))
                    else:
                        # Mock data (already a dictionary) or simple object
                        if isinstance(p, dict):
                            product_dicts.append(p)
                        else:
                            # Convert simple object to dict
                            product_dict = {}
                            for attr in ['id', 'name', 'description', 'picture', 'categories']:
                                if hasattr(p, attr):
                                    product_dict[attr] = getattr(p, attr)
                            if hasattr(p, 'price_usd'):
                                price_obj = getattr(p, 'price_usd')
                                if hasattr(price_obj, '__dict__'):
                                    product_dict['priceUsd'] = price_obj.__dict__
                                else:
                                    product_dict['priceUsd'] = price_obj
                            product_dicts.append(product_dict)
                
                # Send response back to requester
                await self.send_response(
                    request.sender,
                    request.id,
                    product_dicts,
                    success=True,
                    conversation_id=request.conversation_id
                )
                
                return True
            else:
                logger.warning(f"ProductDiscoveryAgent received unsupported request type: {request.request_type}")
                
                # Send error response
                await self.send_response(
                    request.sender,
                    request.id,
                    [],
                    success=False,
                    error=f"Unsupported request type: {request.request_type}",
                    conversation_id=request.conversation_id
                )
                
                return False
                
        except Exception as e:
            logger.error(f"Error processing request in ProductDiscoveryAgent: {e}")
            
            # Send error notification
            error_notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_error",
                agent_name="Product Discovery Agent",
                agent_id=self.agent_id,
                content=f"Error searching for products: {str(e)}"
            )
            await self.send_message(request.sender, error_notification)
            
            # Send error response
            await self.send_response(
                request.sender,
                request.id,
                [],
                success=False,
                error=str(e),
                conversation_id=request.conversation_id
            )
            
            return False
    
    async def _intelligent_product_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Use AI to intelligently search and filter products based on user query.
        """
        try:
            # Step 1: Get all products from the catalog
            all_products = product_catalog_client.list_products()
            
            if not all_products:
                logger.warning("No products available in catalog")
                return []
            
            # Convert products to dictionaries for analysis
            product_dicts = []
            for p in all_products:
                if hasattr(p, 'DESCRIPTOR'):
                    # Real protobuf object
                    product_dicts.append(MessageToDict(p))
                else:
                    # Mock data (already a dictionary) or simple object
                    if isinstance(p, dict):
                        product_dicts.append(p)
                    else:
                        # Convert simple object to dict
                        product_dict = {}
                        for attr in ['id', 'name', 'description', 'picture', 'categories']:
                            if hasattr(p, attr):
                                product_dict[attr] = getattr(p, attr)
                        if hasattr(p, 'price_usd'):
                            price_obj = getattr(p, 'price_usd')
                            if hasattr(price_obj, '__dict__'):
                                product_dict['priceUsd'] = price_obj.__dict__
                            else:
                                product_dict['priceUsd'] = price_obj
                        product_dicts.append(product_dict)
            
            # Step 2: Use AI to analyze query and filter products
            if self.ai_model:
                filtered_products = await self._ai_filter_products(query, product_dicts)
            else:
                # Fallback to keyword-based filtering
                filtered_products = self._keyword_filter_products(query, product_dicts)
            
            logger.info(f"AI filtering reduced {len(product_dicts)} products to {len(filtered_products)} relevant matches")
            return filtered_products
            
        except Exception as e:
            logger.error(f"Error in intelligent product search: {e}")
            # Fallback to basic search
            return product_catalog_client.search_products(query)
    
    async def _ai_filter_products(self, query: str, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use Vertex AI to intelligently filter products based on user query.
        """
        try:
            # Create product summary for AI analysis
            product_summaries = []
            for i, product in enumerate(products):
                name = product.get('name', 'Unknown')
                description = product.get('description', '')
                categories = product.get('categories', [])
                product_summaries.append(f"{i}: {name} - {description} (Categories: {', '.join(categories)})")
            
            products_text = '\n'.join(product_summaries)
            
            analysis_prompt = f"""
            User Query: "{query}"
            
            Available Products:
            {products_text}
            
            Analyze the user query and identify which products are most relevant. Consider:
            - Direct name matches
            - Category relevance
            - Description keywords
            - User intent (e.g., "shoes" should match footwear)
            
            Return the indices of the most relevant products as a JSON array of numbers.
            If no products match well, return an empty array [].
            If the query is very general (like "what products"), return all indices.
            
            Examples:
            - "shoes" → products with footwear categories
            - "camera" → products with camera in name or description
            - "what products" → all products
            
            Response format: [0, 2, 5] (just the JSON array, nothing else)
            """
            
            response = self.ai_model.generate_content(analysis_prompt)
            response_text = response.text.strip()
            
            # Parse AI response
            import json
            try:
                # Extract JSON if wrapped in markdown
                if "```" in response_text:
                    start = response_text.find("[")
                    end = response_text.rfind("]") + 1
                    response_text = response_text[start:end]
                
                relevant_indices = json.loads(response_text)
                
                # Filter products based on AI selection
                filtered_products = [products[i] for i in relevant_indices if 0 <= i < len(products)]
                
                logger.info(f"AI selected {len(filtered_products)} products from {len(products)} total")
                return filtered_products
                
            except (json.JSONDecodeError, IndexError) as e:
                logger.warning(f"Error parsing AI response: {e}, falling back to keyword filtering")
                return self._keyword_filter_products(query, products)
                
        except Exception as e:
            logger.error(f"Error in AI product filtering: {e}")
            return self._keyword_filter_products(query, products)
    
    def _keyword_filter_products(self, query: str, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fallback keyword-based product filtering.
        """
        query_lower = query.lower()
        
        # If query is very general, return all products
        general_queries = ["what products", "show me", "available", "catalog", "items"]
        if any(gen_query in query_lower for gen_query in general_queries):
            return products
        
        filtered_products = []
        
        for product in products:
            name = product.get('name', '').lower()
            description = product.get('description', '').lower()
            categories = [cat.lower() for cat in product.get('categories', [])]
            
            # Check for direct matches
            search_terms = query_lower.split()
            
            for term in search_terms:
                if (term in name or 
                    term in description or 
                    any(term in cat for cat in categories) or
                    self._matches_category_keywords(term, categories)):
                    filtered_products.append(product)
                    break
        
        return filtered_products
    
    def _matches_category_keywords(self, term: str, product_categories: List[str]) -> bool:
        """
        Check if search term matches category keywords.
        """
        for category, keywords in self.category_keywords.items():
            if term in keywords and category in product_categories:
                return True
        return False

# Singleton instance
product_discovery_agent = ProductDiscoveryAgent()
