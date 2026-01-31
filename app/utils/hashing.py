"""
Hashing utilities for audit trail tamper-evident hashing.
"""

import hashlib
import json
from typing import Any, Dict


def hash_payload(payload: Dict[str, Any]) -> str:
    """
    Generate SHA-256 hash of a payload for audit trail.
    
    Args:
        payload: Dictionary to hash
        
    Returns:
        Hexadecimal SHA-256 hash string
    """
    # Sort keys for consistent hashing
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(payload_str.encode()).hexdigest()

