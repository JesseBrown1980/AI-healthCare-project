"""
HL7 v2.x message router.

Routes messages by type to appropriate handlers.
"""

import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class HL7MessageRouter:
    """Router for HL7 v2.x messages by type."""
    
    def __init__(self):
        """Initialize message router."""
        self.handlers: Dict[str, Callable] = {}
    
    def register_handler(self, message_type: str, handler: Callable) -> None:
        """
        Register a handler for a specific message type.
        
        Args:
            message_type: Message type pattern (e.g., "ADT^A01", "ORU^R01", or "ADT^*" for all ADT)
            handler: Callable that processes the message
        """
        self.handlers[message_type] = handler
        logger.info("Registered handler for message type: %s", message_type)
    
    def route(self, parsed_message: Dict[str, Any]) -> Optional[Any]:
        """
        Route a parsed message to the appropriate handler.
        
        Args:
            parsed_message: Parsed HL7 message from HL7MessageParser
            
        Returns:
            Result from handler, or None if no handler found
        """
        message_type = parsed_message.get("message_type")
        if not message_type:
            logger.warning("Message has no message_type, cannot route")
            return None
        
        # Try exact match first
        handler = self.handlers.get(message_type)
        if handler:
            logger.debug("Routing message type %s to handler", message_type)
            return handler(parsed_message)
        
        # Try wildcard match (e.g., "ADT^*" for any ADT message)
        message_category = message_type.split("^")[0] if "^" in message_type else message_type
        wildcard_key = f"{message_category}^*"
        handler = self.handlers.get(wildcard_key)
        if handler:
            logger.debug("Routing message type %s to wildcard handler %s", message_type, wildcard_key)
            return handler(parsed_message)
        
        logger.warning("No handler found for message type: %s", message_type)
        return None
    
    def get_supported_types(self) -> list[str]:
        """Get list of supported message types."""
        return list(self.handlers.keys())
