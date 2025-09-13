# CartMate - AI Shopping Assistant

CartMate is an intelligent, conversational shopping assistant powered by Google's Vertex AI and built with a sophisticated multi-agent architecture. It provides personalized shopping experiences through natural language conversations, style analysis, product discovery, and intelligent cart management.

## 🚀 Features

### Core Capabilities
- **Conversational Shopping**: Natural language interactions with AI-powered shopping assistance
- **Style Analysis**: Image-based style profiling and preference learning using Google Vision AI
- **Product Discovery**: Intelligent product search and filtering with style context awareness
- **Price Comparison**: Real-time price monitoring across multiple retailers
- **Cart Management**: Smart cart operations with style coherence validation
- **Real-time Communication**: WebSocket-based instant messaging and updates

### Multi-Agent Architecture
CartMate uses specialized AI agents that work together seamlessly:

- **🤖 Orchestrator Agent**: Primary conversational AI that coordinates all interactions
- **🎨 Style Profiler Agent**: Analyzes user images to build style preferences
- **🔍 Product Discovery Agent**: Searches and filters products based on style context
- **💰 Price Comparison Agent**: Finds competitive pricing across external retailers
- **🛒 Cart Management Agent**: Handles shopping cart operations with intelligent validation

## 🏗️ Architecture

### Technology Stack
- **Frontend**: React 18 + TypeScript + Tailwind CSS + Vite
- **Backend**: Python 3.11+ + FastAPI + Redis + WebSockets
- **AI/ML**: Google Vertex AI (Gemini, Vision API)
- **Communication**: A2A (Agent-to-Agent) protocol with Redis pub/sub
- **External Services**: Online Boutique (gRPC), Perplexity API
- **Deployment**: Kubernetes + Docker + Google Cloud Platform

### System Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend│    │  FastAPI Backend│    │  Google Vertex  │
│   (TypeScript)  │◄──►│   (Python)      │◄──►│      AI         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │  Redis Message  │              │
         └──────────────►│      Bus        │◄─────────────┘
                        └─────────────────┘
                                 │
                        ┌─────────────────┐
                        │  Multi-Agent    │
                        │   System        │
                        └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Redis server
- Google Cloud Platform account with Vertex AI enabled
- Docker (optional, for containerized deployment)

### Backend Setup
```bash
# Navigate to backend directory
cd cartmate-backend

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your Google Cloud credentials and Redis configuration

# Run the backend server
python main.py
```

### Frontend Setup
```bash
# Navigate to frontend directory
cd cartmate-frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up --build

# Or deploy to Kubernetes
kubectl apply -f k8s/
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the backend directory:

```env
# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_LOCATION=us-central1

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your-redis-password

# External APIs
PERPLEXITY_API_KEY=your-perplexity-api-key

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
```

## 📁 Project Structure

```
CartMate/
├── cartmate-backend/           # Python FastAPI backend
│   ├── agents/                 # AI agent implementations
│   │   ├── orchestrator_refactored.py
│   │   ├── product_discovery.py
│   │   ├── price_comparison.py
│   │   └── cart_management.py
│   ├── a2a/                    # Agent-to-Agent protocol
│   │   ├── coordinator.py
│   │   └── message_bus.py
│   ├── api/                    # WebSocket and HTTP endpoints
│   ├── services/               # External service integrations
│   ├── models/                 # Data models and validation
│   └── tests/                  # Test suites
├── cartmate-frontend/          # React TypeScript frontend
│   ├── src/
│   │   ├── components/         # React components
│   │   │   ├── chat/           # Chat interface components
│   │   │   ├── ui/             # UI components
│   │   │   └── promotions/     # Ad components
│   │   ├── services/           # API service clients
│   │   └── utils/              # Utility functions
│   └── public/                 # Static assets
├── k8s/                        # Kubernetes deployment files
└── deploy-*.ps1               # Deployment scripts
```

## 🧪 Testing

### Backend Tests
```bash
cd cartmate-backend
# Activate virtual environment first
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Run all tests
pytest

# Run specific test files
pytest tests/test_websocket.py
pytest tests/test_core_infrastructure.py
```

### Frontend Tests
```bash
cd cartmate-frontend
npm test
```

## 🚀 Deployment

### Local Development
```bash
# Start Redis server
redis-server

# Start backend (in one terminal)
cd cartmate-backend
venv\Scripts\activate
python main.py

# Start frontend (in another terminal)
cd cartmate-frontend
npm run dev
```

### Production Deployment
```bash
# Deploy to Google Cloud Platform
./deploy-cloud.ps1

# Deploy to Kubernetes
./deploy.ps1

# Deploy with Docker
docker-compose up --build
```

## 🔍 API Endpoints

### WebSocket Endpoints
- `ws://localhost:8000/ws/chat` - Main chat interface
- `ws://localhost:8000/ws/backchannel` - Agent-to-agent monitoring

### HTTP Endpoints
- `GET /` - Welcome message
- `GET /health` - Health check
- `GET /agents/status` - Agent status information
- `GET /port-forwarding/status` - Port forwarding status

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use TypeScript strict mode for frontend
- Write comprehensive tests for new features
- Document complex business logic
- Use structured logging with correlation IDs

## 📊 Monitoring & Health Checks

CartMate includes comprehensive monitoring:
- **Health Endpoint**: `/health` - System status and component health
- **Agent Status**: `/agents/status` - Individual agent status
- **Port Forwarding**: `/port-forwarding/status` - External service connectivity
- **Real-time Logging**: Structured logging with correlation IDs

## 🔒 Security

- Environment-based configuration management
- Secure WebSocket connections
- Input validation and sanitization
- Rate limiting and error handling
- Google Cloud IAM integration

## 📈 Performance

- Redis-based caching and session management
- Asynchronous processing with FastAPI
- WebSocket-based real-time communication
- Optimized AI model inference
- Horizontal scaling with Kubernetes

## 🐛 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Check if Redis is running
   redis-cli ping
   # Should return PONG
   ```

2. **Google Cloud Authentication**
   ```bash
   # Set up authentication
   gcloud auth application-default login
   # Or set GOOGLE_APPLICATION_CREDENTIALS
   ```

3. **Port Conflicts**
   ```bash
   # Check if ports are in use
   netstat -an | findstr :8000  # Windows
   lsof -i :8000                # Linux/Mac
   ```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google Vertex AI for powerful AI capabilities
- FastAPI for the excellent Python web framework
- React and TypeScript for the modern frontend
- Redis for reliable message queuing and caching

---

**CartMate** - Your intelligent shopping companion powered by AI 🤖🛒