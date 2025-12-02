"""
Event Bus - Real-time event system for monitoring and logging
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class EventBus:
    """
    Event bus for real-time workflow monitoring.
    
    Supports:
    - Event emission
    - Event subscriptions
    - Logging integration
    - Metrics collection
    """
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.event_history: List[Dict] = []
        self.max_history = 1000
    
    async def emit(self, event_type: str, data: Dict[str, Any]):
        """
        Emit an event.
        
        Args:
            event_type: Event type (e.g., "workflow.started")
            data: Event data
        """
        event = {
            "type": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Log event
        logger.info(f"Event: {event_type}", extra={"event_data": data})
        
        # Notify subscribers
        subscribers = self.subscribers.get(event_type, [])
        subscribers.extend(self.subscribers.get("*", []))  # Wildcard subscribers
        
        for callback in subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in event subscriber: {e}")
    
    def subscribe(self, event_type: str, callback: Callable):
        """
        Subscribe to events.
        
        Args:
            event_type: Event type or "*" for all events
            callback: Callback function (can be async)
        """
        self.subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Unsubscribe from events"""
        if callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
    
    def get_history(self, event_type: Optional[str] = None) -> List[Dict]:
        """Get event history"""
        if event_type:
            return [
                e for e in self.event_history
                if e["type"] == event_type
            ]
        return self.event_history
    
    async def close(self):
        """Cleanup"""
        self.subscribers.clear()
        self.event_history.clear()

