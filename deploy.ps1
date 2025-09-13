# CartMate Deployment Script for GKE (PowerShell)
# This script builds, pushes, and deploys CartMate to your existing GKE cluster

Write-Host "🚀 Starting CartMate deployment to GKE..." -ForegroundColor Green

# Configuration
$PROJECT_ID = "imposing-kite-461508-v4"
$REGION = "us-central1"
$CLUSTER_NAME = "boutique-cluster"
$REGISTRY = "gcr.io"

try {
    # 1. Configure Docker to use gcloud as a credential helper
    Write-Host "📋 Configuring Docker authentication..." -ForegroundColor Yellow
    gcloud auth configure-docker

    # 2. Build and push backend image
    Write-Host "🔨 Building CartMate backend..." -ForegroundColor Yellow
    Set-Location cartmate-backend
    docker build -t "$REGISTRY/$PROJECT_ID/cartmate-backend:latest" .
    docker push "$REGISTRY/$PROJECT_ID/cartmate-backend:latest"
    Set-Location ..

    # 3. Build and push frontend image
    Write-Host "🔨 Building CartMate frontend..." -ForegroundColor Yellow
    Set-Location cartmate-frontend
    docker build -t "$REGISTRY/$PROJECT_ID/cartmate-frontend:latest" .
    docker push "$REGISTRY/$PROJECT_ID/cartmate-frontend:latest"
    Set-Location ..

    # 4. Deploy to Kubernetes
    Write-Host "🚀 Deploying to Kubernetes..." -ForegroundColor Yellow
    kubectl apply -f k8s/cartmate-backend-deployment.yaml
    kubectl apply -f k8s/cartmate-frontend-deployment.yaml

    # 5. Wait for deployments to be ready
    Write-Host "⏳ Waiting for deployments to be ready..." -ForegroundColor Yellow
    kubectl rollout status deployment/cartmate-backend
    kubectl rollout status deployment/cartmate-frontend

    # 6. Get external IP
    Write-Host "🌐 Getting external IP..." -ForegroundColor Yellow
    kubectl get svc cartmate-frontend

    Write-Host "✅ CartMate deployment complete!" -ForegroundColor Green
    Write-Host "🎉 Your CartMate app should be accessible via the LoadBalancer IP above" -ForegroundColor Green
    Write-Host "🔗 CartMate will automatically connect to the existing Online Boutique services in the cluster" -ForegroundColor Green

} catch {
    Write-Host "❌ Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
