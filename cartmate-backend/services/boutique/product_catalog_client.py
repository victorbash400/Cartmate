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
        print(f"DEBUG: Attempting to search products with query: '{query}'")
        print(f"DEBUG: gRPC host: {self.host}")
        
        try:
            # First try to search with the query
            request = demo_pb2.SearchProductsRequest(query=query)
            print(f"DEBUG: Sending search request to gRPC service...")
            response = self.stub.SearchProducts(request)
            print(f"DEBUG: Received response with {len(response.results)} results")
            
            # If search returns no results, try listing all products as fallback
            if not response.results:
                print(f"Search for '{query}' returned 0 results, trying list_products as fallback")
                all_products = self.list_products()
                print(f"list_products returned {len(all_products)} products")
                return all_products
            
            print(f"Search for '{query}' returned {len(response.results)} products")
            # Debug: Print first product details
            if response.results:
                first_product = response.results[0]
                print(f"DEBUG: First product - ID: {first_product.id}, Name: {first_product.name}, Picture: {first_product.picture}")
            
            return response.results
        except grpc.RpcError as e:
            print(f"ERROR: gRPC error searching products for '{query}': {e}")
            print(f"DEBUG: Returning empty list instead of mock products")
            # Return empty list when service is unavailable
            return []
        except Exception as e:
            print(f"ERROR: Unexpected error searching products for '{query}': {e}")
            print(f"DEBUG: Returning empty list instead of mock products")
            return []
    
    async def get_product(self, product_id: str):
        """Get a single product by ID"""
        try:
            request = demo_pb2.GetProductRequest(id=product_id)
            response = self.stub.GetProduct(request)
            
            # Convert protobuf to dict
            return {
                "id": response.id,
                "name": response.name,
                "description": response.description,
                "picture": response.picture,
                "price_usd": {
                    "currency_code": response.price_usd.currency_code,
                    "units": response.price_usd.units,
                    "nanos": response.price_usd.nanos
                },
                "categories": list(response.categories)
            }
        except grpc.RpcError as e:
            print(f"Error getting product {product_id}: {e}")
            # Try to find in mock products as fallback
            for mock_product in self._get_mock_products(""):
                if mock_product['id'] == product_id:
                    return mock_product
            return None
        except Exception as e:
            print(f"Unexpected error getting product {product_id}: {e}")
            return None
    
    def _get_mock_products(self, query: str):
        """Return mock products when gRPC service is unavailable"""
        # Create mock product data based on real Online Boutique products
        mock_products = [
            {
                'id': 'OLJCESPC7Z',
                'name': 'Vintage Camera Lens',
                'description': 'A vintage camera lens perfect for photography enthusiasts',
                'picture': 'https://storage.googleapis.com/microservices-demo/images/camera-lens.jpg',
                'priceUsd': {'currencyCode': 'USD', 'units': 67, 'nanos': 990000000},
                'categories': ['photography', 'vintage']
            },
            {
                'id': '66VCHSJNUP', 
                'name': 'Bamboo Glass Jar',
                'description': 'Eco-friendly bamboo lid glass jar for storage',
                'picture': 'https://storage.googleapis.com/microservices-demo/images/bamboo-glass-jar.jpg',
                'priceUsd': {'currencyCode': 'USD', 'units': 5, 'nanos': 490000000},
                'categories': ['home', 'eco-friendly']
            },
            {
                'id': 'L9ECAV7KIM',
                'name': 'Orange Hoodie',
                'description': 'Comfortable orange hoodie perfect for casual wear',
                'picture': 'https://storage.googleapis.com/microservices-demo/images/orange-hoodie.jpg', 
                'priceUsd': {'currencyCode': 'USD', 'units': 49, 'nanos': 990000000},
                'categories': ['clothing', 'hoodies']
            },
            {
                'id': '0PUK6V6EV0',
                'name': 'Stainless Steel Mug',
                'description': 'Durable stainless steel travel mug with lid',
                'picture': 'https://storage.googleapis.com/microservices-demo/images/steel-mug.jpg',
                'priceUsd': {'currencyCode': 'USD', 'units': 24, 'nanos': 990000000},
                'categories': ['drinkware', 'travel']
            },
            {
                'id': 'LS4PSXUNUM',
                'name': 'Sunglasses',
                'description': 'Stylish sunglasses for outdoor activities',
                'picture': 'https://storage.googleapis.com/microservices-demo/images/sunglasses.jpg',
                'priceUsd': {'currencyCode': 'USD', 'units': 19, 'nanos': 990000000},
                'categories': ['accessories', 'outdoor']
            },
            {
                'id': '9SIQT8TOJO',
                'name': 'Tank Top',
                'description': 'Comfortable cotton tank top',
                'picture': 'https://storage.googleapis.com/microservices-demo/images/tank-top.jpg',
                'priceUsd': {'currencyCode': 'USD', 'units': 18, 'nanos': 990000000},
                'categories': ['clothing', 'tops']
            },
            {
                'id': 'L9ECAV7KIM',
                'name': 'Watch',
                'description': 'Elegant wristwatch with leather strap',
                'picture': 'https://storage.googleapis.com/microservices-demo/images/watch.jpg',
                'priceUsd': {'currencyCode': 'USD', 'units': 109, 'nanos': 990000000},
                'categories': ['accessories', 'watches']
            },
            {
                'id': '2ZYFJ3GM2N',
                'name': 'Loafers',
                'description': 'Comfortable leather loafers',
                'picture': 'https://storage.googleapis.com/microservices-demo/images/loafers.jpg',
                'priceUsd': {'currencyCode': 'USD', 'units': 89, 'nanos': 990000000},
                'categories': ['footwear', 'shoes']
            },
            {
                'id': 'IH9J3K2K2K',
                'name': 'Hairdryer',
                'description': 'Professional hairdryer with multiple settings',
                'picture': 'https://storage.googleapis.com/microservices-demo/images/hairdryer.jpg',
                'priceUsd': {'currencyCode': 'USD', 'units': 24, 'nanos': 990000000},
                'categories': ['beauty', 'electronics']
            }
        ]
        
        # Return simple dictionaries instead of mock protobuf objects
        # This avoids the DESCRIPTOR attribute error when using MessageToDict
        return mock_products

# Singleton instance
product_catalog_client = ProductCatalogClient()
