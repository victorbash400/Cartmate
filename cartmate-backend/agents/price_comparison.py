import logging
import asyncio
import requests
from typing import List, Dict, Any, Optional
from agents.base import BaseAgent
from models.a2a import A2AMessage, A2ARequest, A2AResponse, A2AMessageType, A2ARequestType, A2AFrontendNotification
from config.settings import settings

logger = logging.getLogger(__name__)

class PriceComparisonAgent(BaseAgent):
    """
    AI-powered price comparison agent that uses Perplexity Sonar API to find
    competitive pricing and similar products across online retailers.
    """
    
    def __init__(self):
        super().__init__("price_comparison_001", "price_comparison")
        self.registration.capabilities = [
            "compare_prices", 
            "find_similar_products", 
            "price_analysis",
            "market_research",
            "price_trends"
        ]
        
        # Perplexity API configuration
        self.api_url = "https://api.perplexity.ai/chat/completions"
        self.api_key = settings.SONAR_API_KEY or settings.PERPLEXITY_API_KEY
        
        if not self.api_key:
            logger.warning("PERPLEXITY_API_KEY not found in environment variables")
    
    async def start(self):
        """Start the price comparison agent"""
        await super().start()
        logger.info("Price Comparison Agent started")

    async def handle_message(self, message: A2AMessage) -> bool:
        """
        Handle incoming A2A messages.
        """
        try:
            if message.type == A2AMessageType.REQUEST:
                if isinstance(message, A2ARequest):
                    return await self.handle_request(message)
                else:
                    logger.error(f"Received REQUEST message but it's not an A2ARequest: {type(message)}")
                    return False
            else:
                logger.info(f"PriceComparisonAgent received {message.type} message: {message.content}")
                return True
        except Exception as e:
            logger.error(f"Error handling message in PriceComparisonAgent: {e}")
            return False

    async def handle_request(self, request: A2ARequest) -> bool:
        """
        Handle incoming requests from other agents.
        """
        logger.info(f"PriceComparisonAgent received request: {request.request_type}")
        
        try:
            if request.request_type == A2ARequestType.COMPARE_PRICES:
                product_info = request.content.get("product", {})
                session_id = request.content.get("session_id", "")
                logger.info(f"Comparing prices for product: {product_info.get('name', 'Unknown')}")
                
                # Perform price comparison using Perplexity Sonar with detailed step tracking
                price_comparison_data = await self._compare_prices_with_sonar(product_info, session_id)
                logger.info(f"Price comparison completed. Found {len(price_comparison_data.get('similar_products', []))} similar products")
                
                # Send response back to requester
                await self.send_response(
                    request.sender,
                    request.id,
                    price_comparison_data,
                    success=True,
                    conversation_id=request.conversation_id
                )
                
                return True
            else:
                logger.warning(f"PriceComparisonAgent received unsupported request type: {request.request_type}")
                
                # Send error response
                await self.send_response(
                    request.sender,
                    request.id,
                    {},
                    success=False,
                    error=f"Unsupported request type: {request.request_type}",
                    conversation_id=request.conversation_id
                )
                
                return False
                
        except Exception as e:
            logger.error(f"Error processing request in PriceComparisonAgent: {e}")
            
            # Let the orchestrator handle error notifications
            
            # Send error response
            await self.send_response(
                request.sender,
                request.id,
                {},
                success=False,
                error=str(e),
                conversation_id=request.conversation_id
            )
            
            return False
    
    async def _generate_search_query(self, product_info: Dict[str, Any], current_price: str) -> str:
        """
        Use AI to generate an intelligent, contextual search query for price comparison.
        """
        try:
            # Use Vertex AI to generate a smart search query
            from services.vertex_ai_utils import initialize_vertex_ai
            
            model = initialize_vertex_ai()
            if not model:
                logger.error("Failed to initialize Vertex AI for price comparison query generation")
                return f"price comparison {product_info.get('name', 'product')} {current_price}"
            
            product_name = product_info.get('name', 'Unknown Product')
            product_description = product_info.get('description', '')
            categories = product_info.get('categories', [])
            
            query_generation_prompt = f"""
            Generate a smart, focused search query for price comparison research.
            
            Product: {product_name}
            Description: {product_description}
            Categories: {', '.join(categories)}
            Current Price: {current_price}
            
            Create a search query that will find:
            1. Current market prices for this exact product or very similar products
            2. Price comparison across major retailers
            3. Whether {current_price} is a good deal, fair price, or overpriced
            4. Any current sales, discounts, or better alternatives
            
            Make the query specific to this product type and price point. Be concise but comprehensive.
            Focus on getting actionable price comparison data.
            
            Return ONLY the search query, nothing else.
            """
            
            response = model.generate_content(query_generation_prompt)
            search_query = response.text.strip()
            
            logger.info(f"AI-generated search query: {search_query}")
            return search_query
            
        except Exception as e:
            logger.error(f"Error generating AI search query: {e}")
            # Fallback to a simple query
            product_name = product_info.get('name', 'Unknown Product')
            return f"Find current market prices and price comparison for {product_name} at {current_price}. Is this a good deal?"
    
    async def _compare_prices_with_sonar(self, product_info: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """
        Use Perplexity Sonar API to find competitive pricing and similar products.
        """
        try:
            if not self.api_key:
                logger.error("Perplexity API key not available")
                # Provide a helpful fallback response
                product_name = product_info.get('name', 'Unknown Product')
                current_price = product_info.get('priceUsd', {})
                
                # Format current price
                current_price_str = "Unknown"
                if isinstance(current_price, dict):
                    units = current_price.get('units', 0)
                    nanos = current_price.get('nanos', 0)
                    current_price_str = f"${units}.{str(nanos)[:2]}"
                elif current_price:
                    current_price_str = f"${current_price}"
                
                return {
                    "original_product": product_info,
                    "current_price": current_price_str,
                    "price_analysis": f"Price comparison service is currently unavailable. The {product_name} is priced at {current_price_str}. To get competitive pricing analysis, please ensure the Perplexity API key is properly configured.",
                    "similar_products": [],
                    "sources": [],
                    "citations": [],
                    "raw_content": "Price comparison service unavailable - API key not configured",
                    "api_usage": {},
                    "total_cost": 0,
                    "error": "Price comparison service unavailable - API key not configured"
                }
            
            # Extract product details
            product_name = product_info.get('name', 'Unknown Product')
            product_description = product_info.get('description', '')
            product_price = product_info.get('priceUsd', {})
            
            # Format current price
            current_price_str = "Unknown"
            if isinstance(product_price, dict):
                units = product_price.get('units', 0)
                nanos = product_price.get('nanos', 0)
                current_price_str = f"${units}.{str(nanos)[:2]}"
            elif product_price:
                current_price_str = f"${product_price}"
            
            # Generate intelligent search query using AI
            search_query = await self._generate_search_query(product_info, current_price_str)
            
            # Send detailed step notification about the search query
            if session_id:
                from api.websocket import websocket_gateway, AgentStep
                step_notification = [
                    AgentStep(
                        id="searching",
                        type="processing",
                        agent_name="Price Comparison Agent",
                        message=f"Searching: \"{search_query[:80]}{'...' if len(search_query) > 80 else ''}\""
                    )
                ]
                await websocket_gateway.update_agent_communication(session_id, step_notification)
            
            # Make request to Perplexity Sonar API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "user", "content": search_query}
                ]
            }
            
            logger.info(f"Making request to Perplexity Sonar API for product: {product_name}")
            
            # Send API request step
            if session_id:
                api_step = [
                    AgentStep(
                        id="searching",
                        type="processing",
                        agent_name="Price Comparison Agent",
                        message="Making API request to Perplexity..."
                    ),
                    AgentStep(
                        id="api_request",
                        type="processing",
                        agent_name="Price Comparison Agent",
                        message="Making API request to Perplexity..."
                    )
                ]
                await websocket_gateway.update_agent_communication(session_id, api_step)
            
            # Use asyncio to make the HTTP request with longer timeout
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(self.api_url, json=payload, headers=headers, timeout=60)
            )
            
            if response.status_code != 200:
                logger.error(f"Perplexity API request failed with status {response.status_code}: {response.text}")
                return {
                    "error": f"Price comparison API error: {response.status_code}",
                    "similar_products": [],
                    "sources": [],
                    "price_analysis": "Unable to retrieve price comparison data"
                }
            
            # Parse response
            api_response = response.json()
            logger.info(f"Perplexity API response received successfully")
            
            # Send parsing step notification
            if session_id:
                parsing_step = [
                    AgentStep(
                        id="searching",
                        type="success",
                        agent_name="Price Comparison Agent",
                        message=f"Searching: \"{search_query[:80]}{'...' if len(search_query) > 80 else ''}\""
                    ),
                    AgentStep(
                        id="api_request",
                        type="success",
                        agent_name="Price Comparison Agent",
                        message="Making API request to Perplexity..."
                    ),
                    AgentStep(
                        id="parsing",
                        type="processing",
                        agent_name="Price Comparison Agent",
                        message="Analyzing market data and extracting insights..."
                    )
                ]
                await websocket_gateway.update_agent_communication(session_id, parsing_step)
            
            # Extract and structure the data
            price_data = self._parse_sonar_response(api_response, product_info, current_price_str)
            
            return price_data
            
        except requests.exceptions.Timeout:
            logger.error("Perplexity API request timed out")
            
            # Send timeout step notification
            if session_id:
                timeout_step = [
                    AgentStep(
                        id="searching",
                        type="error",
                        agent_name="Price Comparison Agent",
                        message="API request timed out - using fallback analysis"
                    )
                ]
                await websocket_gateway.update_agent_communication(session_id, timeout_step)
            
            return {
                "error": "Price comparison request timed out",
                "similar_products": [],
                "sources": [],
                "price_analysis": f"⚠️ **API Timeout** - Unable to retrieve live market data\n\nI couldn't connect to the price comparison service, but the {product_info.get('name', 'product')} is priced at {current_price_str}. For the most accurate pricing, you might want to check major retailers directly."
            }
        except Exception as e:
            logger.error(f"Error in price comparison with Sonar: {e}")
            return {
                "error": f"Price comparison error: {str(e)}",
                "similar_products": [],
                "sources": [],
                "price_analysis": "Unable to perform price comparison"
            }
    
    def _parse_sonar_response(self, api_response: Dict[str, Any], product_info: Dict[str, Any], current_price: str) -> Dict[str, Any]:
        """
        Parse Perplexity Sonar API response and structure the price comparison data.
        """
        try:
            # Extract main content
            choices = api_response.get('choices', [])
            if not choices:
                return {
                    "error": "No price comparison data found",
                    "similar_products": [],
                    "sources": [],
                    "price_analysis": "Unable to find competitive pricing information"
                }
            
            main_content = choices[0].get('message', {}).get('content', '')
            
            # Extract sources and search results
            sources = []
            search_results = api_response.get('search_results', [])
            
            for result in search_results:
                source = {
                    "title": result.get('title', ''),
                    "url": result.get('url', ''),
                    "snippet": result.get('snippet', ''),
                    "date": result.get('date', ''),
                    "last_updated": result.get('last_updated', '')
                }
                sources.append(source)
            
            # Extract citations
            citations = api_response.get('citations', [])
            
            # Parse similar products from the content (this is a simplified approach)
            # In a real implementation, you might want to use AI to extract structured data
            similar_products = self._extract_similar_products_from_content(main_content, product_info)
            
            # Create price analysis
            price_analysis = self._create_price_analysis(main_content, current_price, product_info)
            
            return {
                "original_product": product_info,
                "current_price": current_price,
                "price_analysis": price_analysis,
                "similar_products": similar_products,
                "sources": sources,
                "citations": citations,
                "raw_content": main_content,
                "api_usage": api_response.get('usage', {}),
                "total_cost": api_response.get('usage', {}).get('cost', {}).get('total_cost', 0)
            }
            
        except Exception as e:
            logger.error(f"Error parsing Sonar response: {e}")
            return {
                "error": f"Error parsing price comparison data: {str(e)}",
                "similar_products": [],
                "sources": [],
                "price_analysis": "Unable to parse price comparison results"
            }
    
    def _extract_similar_products_from_content(self, content: str, original_product: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract similar products from the AI-generated content.
        This is a simplified approach - in production, you might want to use AI to extract structured data.
        """
        similar_products = []
        
        # Look for price mentions in the content
        lines = content.split('\n')
        current_product = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for price patterns like $XX.XX
            import re
            price_pattern = r'\$(\d+(?:\.\d{2})?)'
            prices = re.findall(price_pattern, line)
            
            if prices and ('$' in line or 'price' in line.lower()):
                # This line likely contains price information
                product_info = {
                    "name": f"Similar to {original_product.get('name', 'product')}",
                    "price": f"${prices[0]}",
                    "description": line,
                    "source": "Market research",
                    "url": "",
                    "retailer": "Various retailers"
                }
                similar_products.append(product_info)
        
        # Limit to top 5 similar products
        return similar_products[:5]
    
    def _create_price_analysis(self, content: str, current_price: str, product_info: Dict[str, Any]) -> str:
        """
        Create a conversational price analysis from the content with accurate pricing logic.
        """
        try:
            product_name = product_info.get('name', 'product')
            
            # Extract actual prices from similar products to make intelligent comparison
            similar_products = self._extract_similar_products_from_content(content, product_info)
            
            # Parse current price to compare
            current_price_num = self._parse_price(current_price)
            
            # Analyze similar product prices
            similar_prices = []
            for product in similar_products:
                price_str = product.get('price', '')
                price_num = self._parse_price(price_str)
                if price_num > 0:
                    similar_prices.append(price_num)
            
            # Determine verdict based on actual price comparison
            verdict = "Fair price"
            verdict_emoji = "⚖️"
            recommendation = ""
            
            if similar_prices:
                avg_similar_price = sum(similar_prices) / len(similar_prices)
                min_similar_price = min(similar_prices)
                
                # More intelligent pricing logic
                if current_price_num > avg_similar_price * 1.2:  # 20% above average
                    verdict = "Overpriced"
                    verdict_emoji = "❌"
                    recommendation = f"Similar products average ${avg_similar_price:.2f}, with some as low as ${min_similar_price:.2f}. You could save money by shopping around."
                elif current_price_num < avg_similar_price * 0.8:  # 20% below average
                    verdict = "Good deal"
                    verdict_emoji = "✅"
                    recommendation = f"This is actually a great price! Similar products average ${avg_similar_price:.2f}, so you're getting a good deal."
                elif current_price_num <= min_similar_price * 1.1:  # Within 10% of lowest price
                    verdict = "Good deal"
                    verdict_emoji = "✅"
                    recommendation = f"This is competitive pricing - very close to the lowest market price of ${min_similar_price:.2f}."
                else:
                    verdict = "Fair price"
                    verdict_emoji = "⚖️"
                    recommendation = f"Price is reasonable compared to similar products averaging ${avg_similar_price:.2f}."
            else:
                # Fallback to content analysis if no similar prices found
                content_lower = content.lower()
                if any(phrase in content_lower for phrase in ["good deal", "great deal", "excellent price", "bargain", "steal"]):
                    verdict = "Good deal"
                    verdict_emoji = "✅"
                    recommendation = "Market research suggests this is a good deal."
                elif any(phrase in content_lower for phrase in ["overpriced", "expensive", "too high", "not worth", "bad deal"]):
                    verdict = "Overpriced"
                    verdict_emoji = "❌"
                    recommendation = "Market research suggests you might find better prices elsewhere."
                else:
                    recommendation = "Price appears to be in line with market expectations."
            
            # Create conversational analysis
            analysis = f"{verdict_emoji} **{verdict}** at {current_price}\n\n"
            analysis += f"{recommendation}\n\n"
            
            if similar_prices:
                analysis += f"**Price Range Found:** ${min(similar_prices):.2f} - ${max(similar_prices):.2f}\n"
                analysis += f"**Average Similar Price:** ${sum(similar_prices)/len(similar_prices):.2f}\n"
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error creating price analysis: {e}")
            return f"⚖️ **Fair price** at {current_price}\n\nI found this product at {current_price}, but couldn't complete a full price comparison analysis."
    
    def _parse_price(self, price_str: str) -> float:
        """Parse price string to float for comparison."""
        try:
            if not price_str:
                return 0.0
            
            # Remove currency symbols and extract number
            import re
            price_match = re.search(r'(\d+(?:\.\d{2})?)', str(price_str))
            if price_match:
                return float(price_match.group(1))
            return 0.0
        except:
            return 0.0

# Singleton instance
price_comparison_agent = PriceComparisonAgent()
