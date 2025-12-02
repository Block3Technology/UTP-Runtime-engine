"""
Auto-Discovery Layer - Automatically finds and registers UTCP tools
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Optional
import json
import logging

from utcp.utcp_client import UtcpClient
from utcp_text.text_call_template import TextCallTemplate

logger = logging.getLogger(__name__)


class AutoDiscoveryLayer:
    """
    Automatically discovers UTCP manuals and registers tools.
    
    Scans directories for:
    - .utcp.json files
    - .utcp.yaml files
    - OpenAPI specs
    - Custom connector definitions
    """
    
    def __init__(self, utcp_client: UtcpClient, discovery_paths: List[str]):
        self.utcp_client = utcp_client
        self.discovery_paths = [Path(p) for p in discovery_paths]
        self.discovered_manuals: List[str] = []
    
    async def discover_and_register(self) -> int:
        """
        Discover all UTCP manuals and register them.
        
        Returns:
            Number of tools discovered
        """
        total_tools = 0
        
        for path in self.discovery_paths:
            if not path.exists():
                logger.warning(f"Discovery path does not exist: {path}")
                continue
            
            # Scan for UTCP files
            utcp_files = self._scan_for_utcp_files(path)
            
            for file_path in utcp_files:
                try:
                    await self.register_manual(str(file_path))
                    self.discovered_manuals.append(str(file_path))
                    total_tools += 1
                    logger.info(f"Registered manual: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to register {file_path}: {e}")
        
        logger.info(f"Auto-discovery complete: {total_tools} tools registered")
        return total_tools
    
    def _scan_for_utcp_files(self, root_path: Path) -> List[Path]:
        """Scan directory for UTCP manual files"""
        utcp_files = []
        
        # Look for .utcp.json, .utcp.yaml, openapi.json, etc.
        patterns = [
            "**/*.utcp.json",
            "**/*.utcp.yaml",
            "**/*.utcp.yml",
            "**/openapi.json",
            "**/swagger.json"
        ]
        
        for pattern in patterns:
            utcp_files.extend(root_path.glob(pattern))
        
        return utcp_files
    
    async def register_manual(self, manual_path: str):
        """
        Register a UTCP manual from file.
        
        Args:
            manual_path: Path to UTCP manual file
        """
        path = Path(manual_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Manual not found: {manual_path}")
        
        # Determine if it's a UTCP manual or OpenAPI spec
        if path.suffix in ['.json', '.yaml', '.yml']:
            # Register as text-based manual
            template = TextCallTemplate(
                name=path.stem,
                call_template_type="text",
                file_path=str(path)
            )
            
            await self.utcp_client.registerManual(template)
        else:
            raise ValueError(f"Unsupported manual format: {path.suffix}")
    
    async def register_from_url(self, name: str, url: str):
        """
        Register UTCP manual from URL (e.g., OpenAPI spec).
        
        Args:
            name: Name for the manual
            url: URL to fetch manual from
        """
        from utcp_http.http_call_template import HttpCallTemplate
        
        template = HttpCallTemplate(
            name=name,
            call_template_type="http",
            http_method="GET",
            url=url,
            content_type="application/json"
        )
        
        await self.utcp_client.registerManual(template)

