# CartMate Complete Deployment Script for PowerShell
# This script builds and deploys CartMate to your existing Kubernetes cluster

param(
    [string]$PerplexityApiKey = "",
    [string]$SonarApiKey = "",
    [string]$Domain = "cartmate.your-domain.com",
    [switch]$SkipBuild = $false,
    [switch]$SkipSecrets = $false
)

Write-Host "🚀 CartMate Deployment Script Starting..." -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green

# Function to check if command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Check prerequisites
Write-Host "📋 Checking prerequisites..." -ForegroundColor Yellow

if (-not (Test-Command "kubectl")) {
    Write-Host "❌ kubectl is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

if (-not (Test-Command "gcloud")) {
    Write-Host "❌ gcloud is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

Write-Host "✅ All prerequisites found" -ForegroundColor Green

# Check if we're logged into gcloud
Write-Host "🔐 Checking Google Cloud authentication..." -ForegroundColor Yellow
try {
    $currentProject = gcloud config get-value project 2>$null
    if (-not $currentProject) {
        Write-Host "❌ Not logged into Google Cloud. Please run: gcloud auth login" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Authenticated to Google Cloud project: $currentProject" -ForegroundColor Green
} catch {
    Write-Host "❌ Error checking Google Cloud authentication" -ForegroundColor Red
    exit 1
}

# Check if we're connected to the cluster
Write-Host "🔗 Checking Kubernetes cluster connection..." -ForegroundColor Yellow
try {
    $clusterInfo = kubectl cluster-info 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Not connected to Kubernetes cluster. Please run: gcloud container clusters get-credentials boutique-cluster --location us-central1" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Connected to Kubernetes cluster" -ForegroundColor Green
} catch {
    Write-Host "❌ Error checking Kubernetes connection" -ForegroundColor Red
    exit 1
}

# Get API keys if not provided
if (-not $SkipSecrets) {
    if (-not $PerplexityApiKey) {
        $PerplexityApiKey = Read-Host "Enter your Perplexity API key"
    }
    if (-not $SonarApiKey) {
        $SonarApiKey = Read-Host "Enter your Sonar API key (or press Enter to use Perplexity key for both)"
        if (-not $SonarApiKey) {
            $SonarApiKey = $PerplexityApiKey
        }
    }
}

# Build Docker images using Google Cloud Build
if (-not $SkipBuild) {
    Write-Host "🏗️  Building Docker images with Google Cloud Build..." -ForegroundColor Yellow
    
    # Build backend
    Write-Host "Building CartMate Backend with Cloud Build..." -ForegroundColor Cyan
    gcloud builds submit --tag gcr.io/imposing-kite-461508-v4/cartmate-backend:latest ./cartmate-backend
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to build backend image" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Backend image built and pushed successfully" -ForegroundColor Green
    
    # Build frontend
    Write-Host "Building CartMate Frontend with Cloud Build..." -ForegroundColor Cyan
    gcloud builds submit --tag gcr.io/imposing-kite-461508-v4/cartmate-frontend:latest ./cartmate-frontend
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to build frontend image" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Frontend image built and pushed successfully" -ForegroundColor Green
    
} else {
    Write-Host "⏭️  Skipping Cloud Build (using existing images)" -ForegroundColor Yellow
}

# Create secrets
if (-not $SkipSecrets) {
    Write-Host "🔐 Creating Kubernetes secrets..." -ForegroundColor Yellow
    
    # Encode API keys
    $encodedPerplexityKey = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($PerplexityApiKey))
    $encodedSonarKey = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($SonarApiKey))
    
    # Create secret YAML content
    $secretYaml = @"
apiVersion: v1
kind: Secret
metadata:
  name: cartmate-secrets
type: Opaque
data:
  perplexity-api-key: $encodedPerplexityKey
  sonar-api-key: $encodedSonarKey
"@
    
    # Apply secret
    $secretYaml | kubectl apply -f -
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to create secrets" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Secrets created successfully" -ForegroundColor Green
} else {
    Write-Host "⏭️  Skipping secrets creation" -ForegroundColor Yellow
}

# Update ingress with domain
Write-Host "🌐 Updating ingress configuration..." -ForegroundColor Yellow
$ingressContent = Get-Content "k8s/cartmate-ingress.yaml" -Raw
$ingressContent = $ingressContent -replace "cartmate.your-domain.com", $Domain
$ingressContent | Set-Content "k8s/cartmate-ingress-temp.yaml"

# Deploy to Kubernetes
Write-Host "🚀 Deploying to Kubernetes..." -ForegroundColor Yellow

Write-Host "Deploying CartMate Backend..." -ForegroundColor Cyan
kubectl apply -f k8s/cartmate-backend-deployment.yaml
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to deploy backend" -ForegroundColor Red
    exit 1
}

Write-Host "Deploying CartMate Frontend..." -ForegroundColor Cyan
kubectl apply -f k8s/cartmate-frontend-deployment.yaml
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to deploy frontend" -ForegroundColor Red
    exit 1
}

Write-Host "Deploying Ingress..." -ForegroundColor Cyan
kubectl apply -f k8s/cartmate-ingress-temp.yaml
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to deploy ingress" -ForegroundColor Red
    exit 1
}

# Clean up temp file
Remove-Item "k8s/cartmate-ingress-temp.yaml" -ErrorAction SilentlyContinue

Write-Host "✅ All deployments completed successfully!" -ForegroundColor Green

# Wait for deployments to be ready
Write-Host "⏳ Waiting for deployments to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=available --timeout=300s deployment/cartmate-backend
kubectl wait --for=condition=available --timeout=300s deployment/cartmate-frontend

# Get service information
Write-Host "`n📊 Deployment Status:" -ForegroundColor Green
Write-Host "===================" -ForegroundColor Green

Write-Host "`n🔍 Pods:" -ForegroundColor Cyan
kubectl get pods -l app=cartmate-backend
kubectl get pods -l app=cartmate-frontend

Write-Host "`n🌐 Services:" -ForegroundColor Cyan
kubectl get services cartmate-backend cartmate-frontend

Write-Host "`n🔗 Ingress:" -ForegroundColor Cyan
kubectl get ingress cartmate-ingress

# Get external IP
Write-Host "`n🌍 External Access:" -ForegroundColor Green
$frontendService = kubectl get service cartmate-frontend -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null
if ($frontendService) {
    Write-Host "Frontend LoadBalancer IP: http://$frontendService" -ForegroundColor Yellow
}

$ingressIP = kubectl get ingress cartmate-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null
if ($ingressIP) {
    Write-Host "Ingress IP: http://$ingressIP" -ForegroundColor Yellow
    Write-Host "Domain: http://$Domain (if DNS is configured)" -ForegroundColor Yellow
}

Write-Host "`n🎉 CartMate deployment completed successfully!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green

Write-Host "`n📝 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Configure DNS to point $Domain to the ingress IP" -ForegroundColor White
Write-Host "2. Wait a few minutes for all services to be fully ready" -ForegroundColor White
Write-Host "3. Test the application at the URLs above" -ForegroundColor White
Write-Host "4. Check logs with: kubectl logs -l app=cartmate-backend" -ForegroundColor White

Write-Host "`n🔧 Useful Commands:" -ForegroundColor Yellow
Write-Host "kubectl get all -l app=cartmate-backend" -ForegroundColor White
Write-Host "kubectl get all -l app=cartmate-frontend" -ForegroundColor White
Write-Host "kubectl logs -f deployment/cartmate-backend" -ForegroundColor White
Write-Host "kubectl logs -f deployment/cartmate-frontend" -ForegroundColor White
