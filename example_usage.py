"""
Example usage of UTP Runtime Engine
"""

import asyncio
import os
from utp_runtime import UTPRuntimeEngine

async def main():
    # Initialize UTP Runtime Engine
    engine = await UTPRuntimeEngine.create(
        config_path="./utp_config.json",
        discovery_paths=["./tools", "./connectors"]
    )
    
    # Example 1: Simple execution
    result = await engine.execute(
        "Check Betfair markets and get current odds for Premier League"
    )
    print(f"Result: {result}")
    
    # Example 2: Complex multi-step workflow
    result = await engine.execute(
        """
        Check Betfair markets for Premier League,
        analyze historical data from MongoDB,
        if conditions are met, place a lay bet,
        then log the result to Google Sheets
        """,
        session_id="workflow_123"
    )
    print(f"Workflow Result: {result}")
    
    # Example 3: Get available tools
    tools = await engine.get_available_tools()
    print(f"Available tools: {len(tools)}")
    for tool in tools[:5]:
        print(f"  - {tool['name']}: {tool['description']}")
    
    # Example 4: Subscribe to events
    async def on_workflow_event(event):
        print(f"Event: {event['type']}")
    
    engine.event_bus.subscribe("workflow.*", on_workflow_event)
    
    # Cleanup
    await engine.close()

if __name__ == "__main__":
    asyncio.run(main())

