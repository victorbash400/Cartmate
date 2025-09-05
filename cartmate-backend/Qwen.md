# CartMate Backend - Qwen Code Context

## Project Overview

CartMate is an AI-powered shopping assistant that uses Google's A2A (Agent-to-Agent) protocol for intelligent agent communication. The backend serves as a conversational shopping platform that integrates with Online Boutique microservices to provide personalized shopping experiences through style analysis, product discovery, price comparison, and cart management.

The system follows a multi-agent architecture where specialized agents handle different aspects of the shopping experience, coordinated through an orchestrator agent using the A2A protocol for seamless communication.

## Key Components

### 1. Core Infrastructure Layer

#### WebSocket Gateway (`api/websocket.py`)
- Real-time bidirectional communication with frontend
- Key methods: `connect()`, `disconnect()`, `send_message()`, `broadcast_typing()`

#### Session Manager (`services/storage/session_manager.py`)
- Manage user sessions and context persistence
- Key methods: `create_session()`, `get_session()`, `update_context()`, `cleanup_expired_sessions()`

#### Redis Client (`services/storage/redis_client.py`)
- Centralized Redis operations for caching and pub/sub
- Key methods: `get/set/delete()`, `publish/subscribe()`, `store_user_profile()`, `get_cart_state()`

### 2. A2A Protocol Layer

#### A2A Coordinator (`a2a/coordinator.py`)
- Central hub for agent discovery and message routing
- Key methods: `register_agent()`, `discover_agents()`, `route_message()`, `broadcast_message()`

#### A2A Protocol (`a2a/protocol.py`)
- Standardized message format and validation
- Message structure includes: id, from_agent, to_agent, message_type, payload, context, timestamp

#### Message Bus (`a2a/message_bus.py`)
- Redis-based pub/sub for agent communication
- Key methods: `publish_to_agent()`, `subscribe_to_messages()`, `create_agent_channel()`

### 3. Agent Layer

#### Base Agent (`agents/base_agent.py`)
- Common functionality for all agents
- Key methods: `register()`, `handle_message()`, `send_response()`, `log_interaction()`

#### Orchestrator Agent (`agents/orchestrator_agent.py`)
- Primary conversational AI and intelligent coordinator
- Capabilities:
  - Natural conversation using Vertex AI Gemini
  - Intelligent reasoning and context-aware responses
  - Streaming communication showing thinking process
  - Agent orchestration and response synthesis
- Key methods: `process_user_message()`, `analyze_intent()`, `delegate_to_agents()`, `synthesize_response()`, `send_partial_response()`

#### Style Profiler Agent (`agents/style_profiler_agent.py`)
- Image analysis and style preference learning using Vertex AI Vision
- Key methods: `analyze_image()`, `extract_style_elements()`, `update_user_profile()`

#### Product Discovery Agent (`agents/product_discovery_agent.py`)
- Product search and recommendation with Online Boutique integration
- Key methods: `search_products()`, `filter_by_style()`, `rank_by_relevance()`

#### Price Comparison Agent (`agents/price_comparison_agent.py`)
- External price research via Perplexity API
- Key methods: `compare_prices()`, `analyze_deals()`, `set_price_alert()`

#### Cart Management Agent (`agents/cart_management_agent.py`)
- Shopping cart operations with style coherence validation
- Key methods: `add_to_cart()`, `validate_style_coherence()`, `suggest_complementary_items()`

### 4. External Service Integration Layer

#### Vertex AI Client (`services/external/vertex_ai_client.py`)
- Google Cloud AI integration for text and vision analysis

#### Online Boutique Clients (`services/boutique/`)
- gRPC integration with Product Catalog, Cart, Currency, and Payment services

#### Perplexity Client (`services/external/perplexity_client.py`)
- External web search for price comparison

## Data Models

- `UserProfile`: User preferences, style profile, and purchase history
- `StyleProfile`: Color palette, preferred styles, brand preferences
- `Product`: Product information with style tags and availability
- `A2AMessage`: Standardized agent communication format

## Implementation Approach

The design emphasizes incremental development:
1. Start with core orchestrator agent and WebSocket infrastructure
2. Progressively add specialized agents:
   - Style Profiler Agent for image analysis
   - Product Discovery Agent for search functionality
   - Price Comparison Agent for competitive pricing
   - Cart Management Agent for shopping operations

## Error Handling

- Five error categories: User Input, External Service, Agent Communication, Data Persistence, AI Service
- Strategy includes graceful degradation, retry logic, fallback responses, and clear user communication
- Comprehensive error logging for debugging

## Testing Strategy

- Unit testing for agent logic and A2A protocol
- Integration testing for agent communication and WebSocket connections
- Performance testing for concurrent users and response times
- Synthetic test data for style profiles and conversation scenarios