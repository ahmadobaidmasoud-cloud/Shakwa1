"""
Speechmatics integration utilities.
Handles temporary token generation for Speechmatics real-time API.
"""

import os
import httpx
from typing import Optional, Dict, Any
from app.core.config import settings


async def generate_speechmatics_token(
    ttl: int = 60,
) -> Dict[str, Any]:
    """
    Generate a temporary token for Speechmatics real-time API authentication.
    
    Calls Speechmatics' API endpoint to create a temporary key instead of 
    directly using the permanent API key (more secure).
    
    Args:
        ttl: Time-to-live for the token in seconds (default: 60)
    
    Returns:
        Dictionary with 'token' (key_value) and 'ttl'
    
    Raises:
        ValueError: If API key is not configured
        httpx.HTTPError: If the Speechmatics API call fails
    """
    api_key = settings.SPEECHMATICS_API_KEY
    
    if not api_key:
        raise ValueError(
            "Speechmatics API key not configured. "
            "Please set SPEECHMATICS_API_KEY environment variable."
        )
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    
    body = {"ttl": ttl}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://mp.speechmatics.com/v1/api_keys?type=rt",
            headers=headers,
            json=body,
        )
        
        if not response.is_success:
            error_data = response.json()
            raise ValueError(
                f"Failed to get Speechmatics token: {response.status_code} - {error_data}"
            )
        
        data = response.json()
        
        # Response includes key_value (temporary token)
        return {
            "token": data.get("key_value"),
            "ttl": ttl,
        }

