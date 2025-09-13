# CartMate Deployment Script using Google Cloud Build
# This script builds and deploys CartMate using Cloud Build (no local Docker needed)

Write-Host "🚀 Starting CartMate deployment using Cloud Build..." -ForegroundColor Green

# Configuration
$PROJECT_ID = "imposing-kite-461508-v4"
$REGION = "us-central1"
$CLUSTER_NAME = "boutique-cluster"

try {
    # 1. Submit build to Cloud Build
    Write-Host "🔨 Building and deploying CartMate with Cloud Build..." -ForegroundColor Yellow
    gcloud builds submit --config cloudbuild.yaml .

    # 2. Wait for deployments to be ready
    Write-Host "⏳ Waiting for deployments to be ready..." -ForegroundColor Yellow
    kubectl rollout status deployment/cartmate-backend
    kubectl rollout status deployment/cartmate-frontend

    # 3. Get external IP
    Write-Host "🌐 Getting external IP..." -ForegroundColor Yellow
    kubectl get svc cartmate-frontend

    Write-Host "✅ CartMate deployment complete!" -ForegroundColor Green
    Write-Host "🎉 Your CartMate app should be accessible via the LoadBalancer IP above" -ForegroundColor Green
    Write-Host "🔗 CartMate will automatically connect to the existing Online Boutique services in the cluster" -ForegroundColor Green

} catch {
    Write-Host "❌ Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
