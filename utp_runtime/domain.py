"""
Domain Logic Layer - Business rules, permissions, rate limiting
"""

from typing import Dict, Optional
import json
from pathlib import Path
import logging

from .events import EventBus

logger = logging.getLogger(__name__)


class DomainLogicLayer:
    """
    Domain logic layer for:
    - Permission management
    - Rate limiting
    - Business rules
    - Security policies
    """
    
    def __init__(self, event_bus: EventBus, config_path: Optional[str] = None):
        self.event_bus = event_bus
        self.permissions: Dict = {}
        self.rate_limits: Dict = {}
        self.business_rules: Dict = {}
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """Load domain configuration"""
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return
        
        with open(path) as f:
            config = json.load(f)
        
        self.permissions = config.get("permissions", {})
        self.rate_limits = config.get("rate_limits", {})
        self.business_rules = config.get("business_rules", {})
    
    async def can_execute(self, tool: str, action: str) -> bool:
        """
        Check if tool/action execution is allowed.
        
        Args:
            tool: Tool name
            action: Action name
        
        Returns:
            True if execution is allowed
        """
        # Check permissions
        tool_perms = self.permissions.get(tool, {})
        
        if not tool_perms.get("enabled", True):
            logger.warning(f"Tool {tool} is disabled")
            return False
        
        allowed_actions = tool_perms.get("allowed_actions", [])
        if allowed_actions and action not in allowed_actions:
            logger.warning(f"Action {action} not allowed for {tool}")
            return False
        
        # Check rate limits
        if not await self._check_rate_limit(tool, action):
            logger.warning(f"Rate limit exceeded for {tool}.{action}")
            return False
        
        # Check business rules
        if not await self._check_business_rules(tool, action):
            logger.warning(f"Business rule violation for {tool}.{action}")
            return False
        
        return True
    
    async def _check_rate_limit(self, tool: str, action: str) -> bool:
        """Check rate limits"""
        # TODO: Implement rate limiting logic
        # Could use Redis, in-memory counters, etc.
        return True
    
    async def _check_business_rules(self, tool: str, action: str) -> bool:
        """Check business rules"""
        # TODO: Implement business rule validation
        # e.g., max bet amounts, trading hours, etc.
        return True
    
    def set_permission(self, tool: str, enabled: bool, allowed_actions: Optional[List] = None):
        """Set permission for a tool"""
        self.permissions[tool] = {
            "enabled": enabled,
            "allowed_actions": allowed_actions or []
        }
    
    def add_business_rule(self, rule_name: str, rule_func):
        """Add a business rule"""
        self.business_rules[rule_name] = rule_func

