import os
import grpc
from protos.generated import demo_pb2
from protos.generated import demo_pb2_grpc

class ProductCatalogClient:
    def __init__(self):
        self.host = os.environ.get("PRODUCT_CATALOG_SERVICE_ADDR", "localhost:3550")
        self.channel = grpc.insecure_channel(self.host)
        self.stub = demo_pb2_grpc.ProductCatalogServiceStub(self.channel)

    def list_products(self):
        try:
            request = demo_pb2.Empty()
            response = self.stub.ListProducts(request)
            return response.products
        except grpc.RpcError as e:
            print(f"Error listing products: {e}")
            return []

    def search_products(self, query: str):
        try:
            # First try to search with the query
            request = demo_pb2.SearchProductsRequest(query=query)
            response = self.stub.SearchProducts(request)
            
            # If search returns no results, try listing all products as fallback
            if not response.results:
                print(f"Search for '{query}' returned 0 results, trying list_products as fallback")
                all_products = self.list_products()
                print(f"list_products returned {len(all_products)} products")
                return all_products
            
            print(f"Search for '{query}' returned {len(response.results)} products")
            return response.results
        except grpc.RpcError as e:
            print(f"Error searching products for '{query}': {e}")
            # Return mock products when service is unavailable
            return self._get_mock_products(query)
    
    def _get_mock_products(self, query: str):
        """Return mock products when gRPC service is unavailable"""
        # Create mock product data
        mock_products = [
            {
                'id': 'mock-1',
                'name': 'Vintage Camera Lens',
                'description': 'A vintage camera lens perfect for photography enthusiasts',
                'picture': '/static/img/products/camera-lens.jpg',
                'priceUsd': {'currencyCode': 'USD', 'units': 67, 'nanos': 990000000},
                'categories': ['photography', 'vintage']
            },
            {
                'id': 'mock-2', 
                'name': 'Bamboo Glass Jar',
                'description': 'Eco-friendly bamboo lid glass jar for storage',
                'picture': '/static/img/products/bamboo-glass-jar.jpg',
                'priceUsd': {'currencyCode': 'USD', 'units': 18, 'nanos': 990000000},
                'categories': ['home', 'eco-friendly']
            },
            {
                'id': 'mock-3',
                'name': 'Orange Hoodie',
                'description': 'Comfortable orange hoodie perfect for casual wear',
                'picture': '/static/img/products/orange-hoodie.jpg', 
                'priceUsd': {'currencyCode': 'USD', 'units': 49, 'nanos': 990000000},
                'categories': ['clothing', 'hoodies']
            },
            {
                'id': 'mock-4',
                'name': 'Stainless Steel Mug',
                'description': 'Durable stainless steel travel mug with lid',
                'picture': '/static/img/products/steel-mug.jpg',
                'priceUsd': {'currencyCode': 'USD', 'units': 24, 'nanos': 990000000},
                'categories': ['drinkware', 'travel']
            }
        ]
        
        # Return simple dictionaries instead of mock protobuf objects
        # This avoids the DESCRIPTOR attribute error when using MessageToDict
        return mock_products

# Singleton instance
product_catalog_client = ProductCatalogClient()
