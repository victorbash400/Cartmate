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
            request = demo_pb2.SearchProductsRequest(query=query)
            response = self.stub.SearchProducts(request)
            return response.results
        except grpc.RpcError as e:
            print(f"Error searching products for '{query}': {e}")
            return []

# Singleton instance
product_catalog_client = ProductCatalogClient()
