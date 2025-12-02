"""
Workflow Orchestrator - Plans and manages multi-step workflows
"""

import json
from typing import Dict, List, Optional, Any
import logging

from utcp.utcp_client import UtcpClient
from langchain_openai import ChatOpenAI
import os

from .executor import ExecutionEngine
from .events import EventBus

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Plans multi-step workflows using LLM reasoning.
    
    Takes natural language requests and converts them into
    executable workflow steps using available UTCP tools.
    """
    
    def __init__(
        self,
        utcp_client: UtcpClient,
        executor: ExecutionEngine,
        event_bus: EventBus,
        llm: Optional[ChatOpenAI] = None
    ):
        self.utcp_client = utcp_client
        self.executor = executor
        self.event_bus = event_bus
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    async def plan_workflow(
        self,
        user_request: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Plan a multi-step workflow from natural language request.
        
        Args:
            user_request: Natural language description of what to do
            context: Additional context for planning
        
        Returns:
            Workflow definition with steps, dependencies, etc.
        """
        # Get available tools
        tools = await self.utcp_client.getTools()
        
        # Format tools for LLM
        tool_schemas = self._format_tools_for_planning(tools)
        
        # Build planning prompt
        prompt = self._build_planning_prompt(
            user_request,
            tool_schemas,
            context
        )
        
        # Get LLM plan
        response = await self.llm.ainvoke(prompt)
        
        # Parse workflow
        workflow = self._parse_workflow(response.content)
        
        # Validate workflow
        validated_workflow = await self._validate_workflow(workflow, tools)
        
        # Emit event
        await self.event_bus.emit("workflow.planned", {
            "workflow": validated_workflow,
            "request": user_request
        })
        
        return validated_workflow
    
    def _format_tools_for_planning(self, tools) -> List[Dict]:
        """Format UTCP tools for LLM planning"""
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
    
    def _build_planning_prompt(
        self,
        user_request: str,
        tool_schemas: List[Dict],
        context: Optional[Dict]
    ) -> str:
        """Build LLM prompt for workflow planning"""
        context_str = ""
        if context:
            context_str = f"\nAdditional Context:\n{json.dumps(context, indent=2)}"
        
        return f"""You are a workflow planning system. Plan a multi-step workflow to accomplish the user's request.

User Request: {user_request}
{context_str}

Available Tools:
{json.dumps(tool_schemas, indent=2)}

Create a workflow plan. Return ONLY valid JSON in this format:
{{
    "steps": [
        {{
            "id": "step_1",
            "tool": "tool_name",
            "action": "action_name",
            "params": {{}},
            "depends_on": [],
            "retry_on_error": true,
            "timeout": 30
        }}
    ],
    "expected_output": "description of final result"
}}

Rules:
- Use tool names exactly as shown (format: manual_name.tool_name)
- Each step can depend on previous steps using step IDs
- Include all required parameters for each tool
- Plan for error handling and retries
- Consider data flow between steps
"""
    
    def _parse_workflow(self, llm_response: str) -> Dict:
        """Parse LLM response into workflow structure"""
        # Try to extract JSON from response
        try:
            # Look for JSON block
            if "```json" in llm_response:
                json_start = llm_response.find("```json") + 7
                json_end = llm_response.find("```", json_start)
                json_str = llm_response[json_start:json_end].strip()
            elif "```" in llm_response:
                json_start = llm_response.find("```") + 3
                json_end = llm_response.find("```", json_start)
                json_str = llm_response[json_start:json_end].strip()
            else:
                # Try to find JSON object
                json_start = llm_response.find("{")
                json_end = llm_response.rfind("}") + 1
                json_str = llm_response[json_start:json_end]
            
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse workflow: {e}")
            raise ValueError(f"Invalid workflow format: {e}")
    
    async def _validate_workflow(
        self,
        workflow: Dict,
        available_tools: List
    ) -> Dict:
        """Validate workflow against available tools"""
        tool_map = {tool.name: tool for tool in available_tools}
        
        validated_steps = []
        for step in workflow.get("steps", []):
            tool_name = step.get("tool")
            
            if tool_name not in tool_map:
                raise ValueError(f"Tool not found: {tool_name}")
            
            # Validate parameters against tool schema
            tool = tool_map[tool_name]
            # TODO: Add parameter validation
            
            validated_steps.append(step)
        
        workflow["steps"] = validated_steps
        return workflow

