"""
Response Formatter Service - Formats agent responses into user-friendly messages
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ResponseFormatter:
    """
    Service for formatting agent responses into conversational, user-friendly messages.
    """
    
    def __init__(self):
        pass

    def format_product_search_response(self, products: List[Dict[str, Any]], session_id: str) -> str:
        """
        Format product search results into a user-friendly response.
        """
        if not products:
            return "I couldn't find any products matching your search. Try different keywords or let me know what specific type of item you're looking for!"
        
        # Since we're sending products as structured data, just provide a clean summary
        response = f"I found {len(products)} products for you! Browse through them below and let me know if you'd like more details about any specific item, or if you'd like to search for something else."
        
        return response

    def format_price_comparison_response(self, price_data: Dict[str, Any], session_id: str) -> str:
        """Format price comparison results into a conversational response."""
        try:
            if price_data.get("error"):
                return f"Sorry, I ran into an issue while checking prices: {price_data['error']}. Let me try again in a moment."
            
            product_name = price_data.get("original_product", {}).get("name", "Unknown Product")
            current_price = price_data.get("current_price", "Unknown")
            price_analysis = price_data.get("price_analysis", "")
            
            response = f"Here's what I found about the {product_name} at {current_price}:\n\n"
            if price_analysis:
                response += f"{price_analysis}\n\n"
            
            similar_products = price_data.get("similar_products", [])
            if similar_products:
                response += f"I found {len(similar_products)} similar options for you:\n"
                for product in similar_products[:3]:
                    name = product.get("name", "Similar product")
                    price = product.get("price", "Unknown")
                    retailer = product.get("retailer", "Various retailers")
                    response += f"• {name} - {price} ({retailer})\n"
                response += "\n"
            
            sources = price_data.get("sources", [])
            if sources:
                response += f"*Based on analysis of {len(sources)} market sources. Prices can vary by location and retailer.*"
            else:
                response += f"*This analysis is based on current market data. Prices may vary by retailer and location.*"
            
            return response
            
        except Exception as e:
            logger.error(f"ResponseFormatter error formatting price comparison response: {e}")
            return "I found some price comparison data, but had trouble formatting it. The analysis is available in the detailed results below."

    def format_cart_management_response(self, cart_data: Dict[str, Any], session_id: str) -> str:
        """Format cart management results into a conversational response."""
        try:
            if not cart_data.get("success", False):
                return "❌ I encountered an issue adding items to your cart. Please try again."
            
            added_items = cart_data.get("added_items", [])
            failed_items = cart_data.get("failed_items", [])
            total_added = cart_data.get("total_added", 0)
            
            if total_added == 0:
                return "❌ No items were added to your cart. Please check the product details and try again."
            
            response = f"✅ Successfully added {total_added} item(s) to your cart!\n\n"
            
            if added_items:
                response += "**Added to cart:**\n"
                for item in added_items:
                    name = item.get("name", "Unknown Product")
                    quantity = item.get("quantity", 1)
                    response += f"• {name} (qty: {quantity})\n"
                response += "\n"
            
            if failed_items:
                response += f"⚠️ Note: {len(failed_items)} item(s) could not be added to your cart.\n\n"
            
            response += "You can view your cart anytime by clicking the cart icon in the sidebar. Would you like to continue shopping or see what's in your cart?"
            
            return response
            
        except Exception as e:
            logger.error(f"ResponseFormatter error formatting cart management response: {e}")
            return "✅ Items have been added to your cart! You can view your cart anytime by clicking the cart icon in the sidebar."

    def format_checkout_response(self, checkout_data: Dict[str, Any], session_id: str) -> str:
        """Format checkout results into a conversational response."""
        try:
            if not checkout_data.get("success", False):
                return "❌ I encountered an issue processing your checkout. Please try again."
            
            order_id = checkout_data.get("order_id", "Unknown")
            shipping_cost = checkout_data.get("shipping_cost", {})
            shipping_address = checkout_data.get("shipping_address", {})
            items = checkout_data.get("items", [])
            
            # Format shipping cost
            if isinstance(shipping_cost, dict):
                cost_units = shipping_cost.get("units", 0)
                cost_nanos = shipping_cost.get("nanos", 0)
                currency = shipping_cost.get("currency_code", "USD")
                shipping_cost_str = f"${cost_units}.{str(cost_nanos)[:2]} {currency}"
            else:
                shipping_cost_str = str(shipping_cost)
            
            # Format shipping address
            address_parts = []
            if shipping_address.get("street_address"):
                address_parts.append(shipping_address["street_address"])
            if shipping_address.get("city"):
                address_parts.append(shipping_address["city"])
            if shipping_address.get("state"):
                address_parts.append(shipping_address["state"])
            if shipping_address.get("zip_code"):
                address_parts.append(shipping_address["zip_code"])
            if shipping_address.get("country"):
                address_parts.append(shipping_address["country"])
            
            address_str = ", ".join(address_parts) if address_parts else "Address not provided"
            
            response = f"🎉 **Order Placed Successfully!**\n\n"
            response += f"**Order ID:** {order_id}\n"
            response += f"**Shipping Cost:** {shipping_cost_str}\n"
            response += f"**Shipping Address:** {address_str}\n\n"
            
            if items:
                response += "**Items Ordered:**\n"
                for item in items:
                    product_id = item.get("item", {}).get("product_id", "Unknown")
                    quantity = item.get("item", {}).get("quantity", 1)
                    cost = item.get("cost", {})
                    
                    if isinstance(cost, dict):
                        cost_units = cost.get("units", 0)
                        cost_nanos = cost.get("nanos", 0)
                        currency = cost.get("currency_code", "USD")
                        cost_str = f"${cost_units}.{str(cost_nanos)[:2]} {currency}"
                    else:
                        cost_str = str(cost)
                    
                    response += f"• {product_id} (qty: {quantity}) - {cost_str}\n"
                response += "\n"
            
            response += "Thank you for your order! You'll receive a confirmation email shortly. "
            response += "You can track your order status anytime by asking me about your order."
            
            return response
            
        except Exception as e:
            logger.error(f"ResponseFormatter error formatting checkout response: {e}")
            return "✅ Your order has been placed successfully! You'll receive a confirmation email shortly."

# Create global instance
response_formatter = ResponseFormatter()
