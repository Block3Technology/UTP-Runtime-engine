# UTP Runtime Engine

A production-grade Universal Tool Protocol Runtime Engine that implements UTCP (Universal Tool Calling Protocol).

## What This Is

**UTCP** = The protocol standard (already exists)  
**UTP Runtime Engine** = The production backend that implements UTCP (what we're building)

## Architecture

```
UTP Runtime Engine
├── Auto-Discovery Layer
├── Workflow Orchestrator  
├── Execution Engine
├── Event Bus & Logging
└── Domain Logic Layer
    └── UTCP Core (foundation)
```

## Features

- ✅ Auto-discovery of UTCP tools
- ✅ Dynamic workflow orchestration
- ✅ Session & state management
- ✅ Event bus for real-time updates
- ✅ Comprehensive logging & monitoring
- ✅ Permission & security layer
- ✅ Multi-step autonomous workflows
- ✅ Retry & error recovery
- ✅ Domain logic separation

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from utp_runtime import UTPRuntimeEngine

# Initialize engine
engine = await UTPRuntimeEngine.create(
    config_path="./utp_config.json"
)

# Execute workflow
result = await engine.execute(
    "Check Betfair markets, analyze history, place bet if conditions met"
)
```

