# CartMate Project (`GEMINI.md`)

This document provides a comprehensive overview of the CartMate project, its architecture, and development conventions to be used as instructional context for AI-assisted development.

## 1. Project Overview

CartMate is an AI-powered, conversational shopping assistant designed to provide a personalized and interactive shopping experience. It consists of two main parts:

*   **`cartmate-frontend`**: A modern web interface built with **React, TypeScript, and Vite**, styled with **Tailwind CSS**. It provides the main chat interface for users to interact with the assistant.
*   **`cartmate-backend`**: A powerful backend service built with **Python and FastAPI**. It features a multi-agent architecture where specialized AI agents collaborate to handle user requests.

The core of the backend is an **Orchestrator Agent** that uses **Vertex AI (Gemini)** to understand user intent. It then delegates tasks to other agents (e.g., `ProductDiscovery`, `StyleProfiler`, `CartManager`) using an **Agent-to-Agent (A2A)** communication protocol built on top of a **Redis** message bus. The system is designed to integrate with external services, such as the **Google Cloud Online Boutique** (via gRPC) for product and cart data, and the **Perplexity API** for price comparisons.

The project's design and requirements are meticulously documented in the `.kiro/specs` directory, which serves as the source of truth for functionality and architecture.

## 2. Building and Running

### Backend (`cartmate-backend`)

1.  **Navigate to Directory**:
    ```bash
    cd cartmate-backend
    ```

2.  **Setup Virtual Environment**:
    ```bash
    # Create the environment
    python -m venv venv

    # Activate the environment
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Server**:
    ```bash
    uvicorn main:app --reload
    ```
    The backend will be running at `http://127.0.0.1:8000`.

### Frontend (`cartmate-frontend`)

1.  **Navigate to Directory**:
    ```bash
    cd cartmate-frontend
    ```

2.  **Install Dependencies**:
    ```bash
    npm install
    ```

3.  **Run the Development Server**:
    ```bash
    npm run dev
    ```
    The frontend will be available at the address provided by Vite (usually `http://localhost:5173`).

### Testing

*   **Backend**: Tests are located in the `tests/` directory and can be run with `pytest`. The `pyproject.toml` file is configured for `pytest`.
    ```bash
    cd cartmate-backend
    pytest
    ```
*   **Frontend**: Linting can be run with `npm run lint`.

## 3. Development Conventions

*   **Architecture**: The backend strictly follows the multi-agent design outlined in `kiro/specs/cartmate-backend/design.md`. New functionality should be implemented within new or existing agents.
*   **Communication**: The primary communication between the frontend and backend is via **WebSockets** (`/ws/chat`). Communication between agents is handled by the A2A protocol over a Redis message bus.
*   **Frontend Structure**: The React application is structured with clear separation of concerns, using components, services, and type definitions. Aliases are configured in `vite.config.ts` for cleaner imports (e.g., `@/components`).
*   **Styling**: The frontend uses **Tailwind CSS**. Utility-first classes should be used for all styling.
*   **Dependencies**: All dependencies must be explicitly added to `requirements.txt` (backend) or `package.json` (frontend).
*   **Documentation**: The `.kiro` directory is the single source of truth for high-level design and requirements. It should be consulted before implementing new features.
