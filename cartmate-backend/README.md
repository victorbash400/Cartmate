# CartMate Backend

AI Shopping Assistant Backend API

## Setup

1. Create virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate virtual environment:
   ```bash
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   uvicorn main:app --reload
   ```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
cartmate-backend/
├── main.py              # Application entry point
├── config/              # Configuration files
├── a2a/                 # A2A protocol implementation
├── agents/              # Agent implementations
├── services/            # External service clients
├── models/              # Data models
├── api/                 # API endpoints
├── utils/               # Utility functions
├── protos/              # gRPC protobuf files
├── kubernetes/          # Kubernetes deployment files
└── requirements.txt     # Python dependencies
```