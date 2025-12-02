# UTP Runtime Engine Architecture

## Overview

The UTP Runtime Engine is a production-grade backend that implements UTCP (Universal Tool Calling Protocol). It provides the missing runtime layer that makes UTCP usable for real-world AI automation.

## Key Components

### 1. Auto-Discovery Layer (`discovery.py`)
- **Purpose**: Automatically finds and registers UTCP tools
- **Features**:
  - Scans directories for `.utcp.json`, `.utcp.yaml`, OpenAPI specs
  - Auto-registers tools without manual configuration
  - Supports URL-based registration
- **Use Case**: "Plug and play" tool addition

### 2. Workflow Orchestrator (`orchestrator.py`)
- **Purpose**: Plans multi-step workflows from natural language
- **Features**:
  - LLM-powered workflow planning
  - Dependency resolution
  - Schema validation
  - Step sequencing
- **Use Case**: "AI, update Shopify inventory and log to Sheets"

### 3. Execution Engine (`executor.py`)
- **Purpose**: Executes workflows with state management
- **Features**:
  - Session management
  - State tracking across steps
  - Retry logic with exponential backoff
  - Error recovery
  - Timeout handling
- **Use Case**: Reliable multi-step execution

### 4. Event Bus (`events.py`)
- **Purpose**: Real-time monitoring and logging
- **Features**:
  - Event emission/subscription
  - Event history
  - Integration with logging
  - Metrics collection
- **Use Case**: Dashboard updates, audit logs

### 5. Domain Logic Layer (`domain.py`)
- **Purpose**: Business rules and security
- **Features**:
  - Permission management
  - Rate limiting
  - Business rule validation
  - Security policies
- **Use Case**: "Max bet $1000", "Only allow during trading hours"

### 6. Main Engine (`engine.py`)
- **Purpose**: Orchestrates all components
- **Features**:
  - Unified API
  - Component initialization
  - Lifecycle management
- **Use Case**: Single entry point for all operations

## Data Flow

```
User Request
    ↓
UTP Runtime Engine
    ↓
Workflow Orchestrator (plans)
    ↓
Execution Engine (executes)
    ↓
UTCP Client (calls tools)
    ↓
External APIs/Tools
    ↓
Results → Event Bus → Dashboard
```

## Session Management

Each workflow execution gets a session:
- Unique session ID
- Workflow definition
- Step results
- State (data passed between steps)
- Errors and retries
- Timestamps

## Event System

Events emitted:
- `workflow.started` - Workflow begins
- `workflow.planned` - LLM has planned steps
- `step.started` - Step execution begins
- `step.completed` - Step succeeds
- `step.failed` - Step fails
- `workflow.completed` - All steps done
- `workflow.error` - Workflow fails

## Permission Model

Three levels:
1. **Tool-level**: Enable/disable entire tools
2. **Action-level**: Allow specific actions per tool
3. **Business rules**: Custom validation logic

Example:
```json
{
  "permissions": {
    "betfair": {
      "enabled": true,
      "allowed_actions": ["listMarkets", "getOdds", "placeBet"]
    }
  },
  "business_rules": {
    "max_bet_amount": 1000
  }
}
```

## Extension Points

### Adding Custom Tools

1. Create UTCP manual file (`.utcp.json`)
2. Place in discovery path
3. Engine auto-discovers and registers

### Adding Business Rules

```python
def max_bet_rule(tool, action, params):
    if action == "placeBet" and params.get("amount", 0) > 1000:
        return False
    return True

engine.domain_layer.add_business_rule("max_bet", max_bet_rule)
```

### Custom Event Handlers

```python
async def on_bet_placed(event):
    # Send notification, log to database, etc.
    pass

engine.event_bus.subscribe("step.completed", on_bet_placed)
```

## Next Steps

1. **Add Connectors**: Create UTCP manuals for Betfair, Shopify, etc.
2. **Build Dashboard**: Web UI for monitoring
3. **Add Persistence**: Store sessions in database
4. **Add Rate Limiting**: Redis-based rate limiting
5. **Add Authentication**: User/API key management
6. **Add Workflow Templates**: Pre-built workflows
7. **Add Testing**: Unit and integration tests

