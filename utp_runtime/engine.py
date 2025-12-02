"""
UTP Runtime Engine - Main orchestration layer
"""

import asyncio
from typing import Dict, Optional, List, Any
from pathlib import Path
import json

from utcp.utcp_client import UtcpClient
from utcp.data.utcp_client_config import UtcpClientConfig

from .discovery import AutoDiscoveryLayer
from .orchestrator import WorkflowOrchestrator
from .executor import ExecutionEngine
from .events import EventBus
from .domain import DomainLogicLayer


class UTPRuntimeEngine:
    """
    Production-grade UTP Runtime Engine that implements UTCP.
    
    This is the missing backend that provides:
    - Auto-discovery of tools
    - Dynamic workflow orchestration
    - Session management
    - Event bus
    - Domain logic separation
    """
    
    def __init__(
        self,
        utcp_client: UtcpClient,
        discovery_layer: AutoDiscoveryLayer,
        orchestrator: WorkflowOrchestrator,
        executor: ExecutionEngine,
        event_bus: EventBus,
        domain_layer: DomainLogicLayer
    ):
        self.utcp_client = utcp_client
        self.discovery_layer = discovery_layer
        self.orchestrator = orchestrator
        self.executor = executor
        self.event_bus = event_bus
        self.domain_layer = domain_layer
    
    @classmethod
    async def create(
        cls,
        config_path: Optional[str] = None,
        utcp_config: Optional[Dict] = None,
        discovery_paths: Optional[List[str]] = None
    ):
        """
        Create and initialize UTP Runtime Engine.
        
        Args:
            config_path: Path to UTP config JSON
            utcp_config: Direct UTCP config dict
            discovery_paths: Paths to scan for UTCP manuals
        """
        # Load config
        if config_path:
            with open(config_path) as f:
                config = json.load(f)
            utcp_config = config.get("utcp", {})
            discovery_paths = config.get("discovery_paths", ["./tools", "./connectors"])
        
        # Initialize UTCP client (foundation)
        utcp_client = await UtcpClient.create(config=utcp_config or {})
        
        # Initialize layers
        discovery_layer = AutoDiscoveryLayer(utcp_client, discovery_paths or [])
        event_bus = EventBus()
        domain_layer = DomainLogicLayer(event_bus)
        executor = ExecutionEngine(utcp_client, domain_layer, event_bus)
        orchestrator = WorkflowOrchestrator(utcp_client, executor, event_bus)
        
        # Auto-discover tools
        await discovery_layer.discover_and_register()
        
        return cls(
            utcp_client=utcp_client,
            discovery_layer=discovery_layer,
            orchestrator=orchestrator,
            executor=executor,
            event_bus=event_bus,
            domain_layer=domain_layer
        )
    
    async def execute(
        self,
        user_request: str,
        session_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: Execute user request as multi-step workflow.
        
        Args:
            user_request: Natural language request
            session_id: Optional session ID for state tracking
            context: Additional context for execution
        
        Returns:
            Execution result with workflow steps and outcomes
        """
        # Emit event
        await self.event_bus.emit("workflow.started", {
            "request": user_request,
            "session_id": session_id
        })
        
        try:
            # 1. Orchestrator plans workflow
            workflow = await self.orchestrator.plan_workflow(
                user_request,
                context=context
            )
            
            # 2. Execute workflow
            result = await self.executor.execute_workflow(
                workflow,
                session_id=session_id
            )
            
            # 3. Emit completion event
            await self.event_bus.emit("workflow.completed", {
                "session_id": session_id,
                "result": result
            })
            
            return result
            
        except Exception as e:
            # Emit error event
            await self.event_bus.emit("workflow.error", {
                "session_id": session_id,
                "error": str(e)
            })
            raise
    
    async def get_available_tools(self) -> List[Dict]:
        """Get all available tools with schemas"""
        tools = await self.utcp_client.getTools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputs": tool.inputs,
                "outputs": tool.outputs,
                "tags": tool.tags
            }
            for tool in tools
        ]
    
    async def register_tool_manual(self, manual_path: str):
        """Manually register a UTCP manual"""
        await self.discovery_layer.register_manual(manual_path)
    
    async def close(self):
        """Cleanup resources"""
        await self.utcp_client.close()
        await self.event_bus.close()

