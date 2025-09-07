# Agent-to-Agent (A2A) Communication System

This document describes the Agent-to-Agent communication system implemented in CartMate.

## Overview

The A2A system enables autonomous agents to communicate with each other using a messaging protocol. Each agent has a unique identifier and can send messages to other agents through a central message bus.

## Key Components

### 1. A2A Message Bus
- Central routing system for agent messages
- Supports direct messaging and broadcasting
- Handles message acknowledgment for reliability

### 2. A2A Coordinator
- Manages agent registration and discovery
- Maintains a registry of available agents by type
- Provides lookup services for agents

### 3. Base Agent Class
- Abstract base class for all agents
- Implements common messaging functionality
- Handles message acknowledgment and retries
- Provides error handling and logging

### 4. Message Types
- **Request**: Agent-to-agent requests with typed content
- **Response**: Responses to requests with success/failure status
- **Notification**: One-way messages for information
- **Acknowledgment**: Confirmation of message receipt
- **Frontend Notification**: Special messages for frontend display

## Agent Interaction Flow

1. Agents register with the A2A coordinator on startup
2. Orchestrator identifies target agent by type using coordinator
3. Orchestrator sends request to target agent via message bus
4. Target agent processes request and sends response
5. Message bus ensures reliable delivery with acknowledgments
6. Frontend notifications are broadcast for UI visibility

## Example: Product Search Flow

1. User asks orchestrator to search for products
2. Orchestrator sends frontend notification: "Searching for products..."
3. Orchestrator finds product discovery agent via coordinator
4. Orchestrator sends search request to product discovery agent
5. Product discovery agent sends notification: "Searching for X"
6. Product discovery agent performs search and responds
7. Orchestrator receives response and sends frontend notification
8. User sees results in chat interface

## Error Handling

- Message acknowledgments ensure delivery confirmation
- Automatic retries for failed messages (up to 3 attempts)
- Error notifications sent to originating agents
- Exponential backoff for retry attempts