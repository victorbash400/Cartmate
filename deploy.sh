#!/bin/bash

# CartMate Deployment Script for GKE
# This script builds, pushes, and deploys CartMate to your existing GKE cluster

set -e

# Configuration
PROJECT_ID="imposing-kite-461508-v4"
REGION="us-central1"
CLUSTER_NAME="boutique-cluster"
REGISTRY="gcr.io"

echo "🚀 Starting CartMate deployment to GKE..."

# 1. Configure Docker to use gcloud as a credential helper
echo "📋 Configuring Docker authentication..."
gcloud auth configure-docker

# 2. Build and push backend image
echo "🔨 Building CartMate backend..."
cd cartmate-backend
docker build -t $REGISTRY/$PROJECT_ID/cartmate-backend:latest .
docker push $REGISTRY/$PROJECT_ID/cartmate-backend:latest
cd ..

# 3. Build and push frontend image
echo "🔨 Building CartMate frontend..."
cd cartmate-frontend
docker build -t $REGISTRY/$PROJECT_ID/cartmate-frontend:latest .
docker push $REGISTRY/$PROJECT_ID/cartmate-frontend:latest
cd ..

# 4. Deploy to Kubernetes
echo "🚀 Deploying to Kubernetes..."
kubectl apply -f k8s/cartmate-backend-deployment.yaml
kubectl apply -f k8s/cartmate-frontend-deployment.yaml

# 5. Wait for deployments to be ready
echo "⏳ Waiting for deployments to be ready..."
kubectl rollout status deployment/cartmate-backend
kubectl rollout status deployment/cartmate-frontend

# 6. Get external IP
echo "🌐 Getting external IP..."
kubectl get svc cartmate-frontend

echo "✅ CartMate deployment complete!"
echo "🎉 Your CartMate app should be accessible via the LoadBalancer IP above"
echo "🔗 CartMate will automatically connect to the existing Online Boutique services in the cluster"
