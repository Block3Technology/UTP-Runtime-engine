"""
Execution Engine - Executes workflows with session management
"""

import uuid
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from utcp.utcp_client import UtcpClient

from .domain import DomainLogicLayer
from .events import EventBus

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Executes multi-step workflows with:
    - Session management
    - State tracking
    - Retry logic
    - Error recovery
    """
    
    def __init__(
        self,
        utcp_client: UtcpClient,
        domain_layer: DomainLogicLayer,
        event_bus: EventBus
    ):
        self.utcp_client = utcp_client
        self.domain_layer = domain_layer
        self.event_bus = event_bus
        self.sessions: Dict[str, Dict] = {}
    
    async def execute_workflow(
        self,
        workflow: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a multi-step workflow.
        
        Args:
            workflow: Workflow definition with steps
            session_id: Optional session ID for state tracking
        
        Returns:
            Execution result with outcomes
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Initialize session
        session = {
            "session_id": session_id,
            "workflow": workflow,
            "started_at": datetime.utcnow().isoformat(),
            "steps": [],
            "state": {},
            "errors": [],
            "status": "running"
        }
        self.sessions[session_id] = session
        
        # Emit start event
        await self.event_bus.emit("execution.started", {
            "session_id": session_id,
            "workflow": workflow
        })
        
        try:
            # Execute steps in order
            for step in workflow.get("steps", []):
                step_result = await self._execute_step(step, session)
                session["steps"].append(step_result)
                
                # Update state with step output
                if step_result.get("success"):
                    step_id = step.get("id", f"step_{len(session['steps'])}")
                    session["state"][step_id] = step_result.get("output")
            
            # Mark as completed
            session["status"] = "completed"
            session["completed_at"] = datetime.utcnow().isoformat()
            
            # Emit completion event
            await self.event_bus.emit("execution.completed", {
                "session_id": session_id,
                "result": session
            })
            
            return {
                "session_id": session_id,
                "status": "completed",
                "steps": session["steps"],
                "final_state": session["state"],
                "errors": session["errors"]
            }
            
        except Exception as e:
            session["status"] = "failed"
            session["failed_at"] = datetime.utcnow().isoformat()
            session["errors"].append({
                "error": str(e),
                "type": type(e).__name__
            })
            
            # Emit error event
            await self.event_bus.emit("execution.failed", {
                "session_id": session_id,
                "error": str(e)
            })
            
            raise
    
    async def _execute_step(
        self,
        step: Dict[str, Any],
        session: Dict
    ) -> Dict[str, Any]:
        """Execute a single workflow step"""
        step_id = step.get("id", f"step_{len(session['steps'])}")
        tool_name = step.get("tool")
        action = step.get("action")
        params = step.get("params", {})
        retry_on_error = step.get("retry_on_error", True)
        max_retries = step.get("max_retries", 3)
        timeout = step.get("timeout", 30)
        
        # Check permissions
        if not await self.domain_layer.can_execute(tool_name, action):
            raise PermissionError(f"Cannot execute {tool_name}.{action}")
        
        # Emit step start event
        await self.event_bus.emit("step.started", {
            "session_id": session["session_id"],
            "step_id": step_id,
            "tool": tool_name,
            "action": action
        })
        
        # Resolve dependencies (use previous step outputs)
        resolved_params = self._resolve_dependencies(params, session)
        
        # Execute with retry logic
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                # Execute tool via UTCP
                result = await asyncio.wait_for(
                    self.utcp_client.call_tool(
                        tool_name=f"{tool_name}.{action}",
                        tool_args=resolved_params
                    ),
                    timeout=timeout
                )
                
                # Emit step success event
                await self.event_bus.emit("step.completed", {
                    "session_id": session["session_id"],
                    "step_id": step_id,
                    "result": result
                })
                
                return {
                    "step_id": step_id,
                    "success": True,
                    "output": result,
                    "retry_count": retry_count
                }
                
            except Exception as e:
                last_error = e
                retry_count += 1
                
                if retry_on_error and retry_count <= max_retries:
                    logger.warning(
                        f"Step {step_id} failed, retrying ({retry_count}/{max_retries}): {e}"
                    )
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                else:
                    break
        
        # Step failed
        error_info = {
            "step_id": step_id,
            "success": False,
            "error": str(last_error),
            "retry_count": retry_count
        }
        
        # Emit step error event
        await self.event_bus.emit("step.failed", {
            "session_id": session["session_id"],
            "step_id": step_id,
            "error": str(last_error)
        })
        
        # Raise if critical, otherwise return error
        if not retry_on_error:
            raise last_error
        
        return error_info
    
    def _resolve_dependencies(
        self,
        params: Dict[str, Any],
        session: Dict
    ) -> Dict[str, Any]:
        """Resolve parameter dependencies from previous steps"""
        resolved = {}
        
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                # Reference to previous step output
                step_ref = value[1:]  # Remove $
                if step_ref in session["state"]:
                    resolved[key] = session["state"][step_ref]
                else:
                    resolved[key] = value  # Keep as-is if not found
            else:
                resolved[key] = value
        
        return resolved
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session state"""
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[Dict]:
        """List all active sessions"""
        return [
            {
                "session_id": sid,
                "status": session["status"],
                "started_at": session.get("started_at"),
                "steps_count": len(session.get("steps", []))
            }
            for sid, session in self.sessions.items()
        ]

