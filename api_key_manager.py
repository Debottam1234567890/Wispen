"""
API Key Manager for handling multiple Gemini API keys with retry logic
=====================================================================

Manages API key rotation and handles 429 (rate limit) errors by
automatically switching to alternate keys.
"""

import os
from typing import List, Optional, Callable
# from colorama import Fore, Style (Removed for Render compatibility)

# Dummy classes to replace colorama
class Fore:
    CYAN = ""
    GREEN = ""
    YELLOW = ""
    RED = ""
    BLUE = ""
    RESET = ""

class Style:
    RESET_ALL = ""


class APIKeyManager:
    """Manages multiple API keys with automatic fallback on rate limits"""
    
    def __init__(self, key_names: List[str] = None):
        """
        Initialize the API key manager
        
        Args:
            key_names: List of environment variable names for API keys
                      Default: ["GEMINI_API_KEY1", "GEMINI_API_KEY2"]
        """
        if key_names is None:
            key_names = ["GEMINI_API_KEY1", "GEMINI_API_KEY2"]
        
        self.key_names = key_names
        self.api_keys = []
        self.current_index = 0
        
        for key_name in key_names:
            key = os.getenv(key_name)
            if key:
                self.api_keys.append(key)
        
        if not self.api_keys:
            raise ValueError(
                f"No API keys found. Please set environment variables: {', '.join(key_names)}"
            )
    
    def get_current_key(self) -> str:
        """Get the current API key"""
        return self.api_keys[self.current_index]
    
    def switch_key(self) -> bool:
        """
        Switch to the next available API key
        
        Returns:
            True if switched successfully, False if no more keys available
        """
        if len(self.api_keys) <= 1:
            return False
        
        next_index = (self.current_index + 1) % len(self.api_keys)
        if next_index != self.current_index:
            self.current_index = next_index
            return True
        
        return False
    
    def get_key_list(self) -> List[str]:
        """Get list of all available keys"""
        return self.api_keys
    
    def reset_to_first(self):
        """Reset to the first API key"""
        self.current_index = 0


def call_gemini_with_retry(
    api_call_func: Callable,
    api_key_manager: APIKeyManager,
    verbose: bool = True,
    max_retries: int = 2
) -> str:
    """
    Execute an API call with automatic retry on rate limit errors
    
    Args:
        api_call_func: Function that takes api_key and returns response.
                      Should raise exception on HTTP error
        api_key_manager: APIKeyManager instance for key rotation
        verbose: Enable logging
        max_retries: Maximum number of retries with different keys
        
    Returns:
        API response text or error message
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            current_key = api_key_manager.get_current_key()
            
            if verbose and attempt > 0:
                key_index = api_key_manager.current_index + 1
                print(
                    f"{Fore.YELLOW}🔄 Retrying with API key #{key_index}...{Style.RESET_ALL}"
                )
            
            response = api_call_func(current_key)
            
            if attempt > 0 and verbose:
                print(f"{Fore.GREEN}✓ Request successful with alternate key{Style.RESET_ALL}")
            
            return response
            
        except Exception as e:
            error_str = str(e)
            last_error = e
            
            if "429" in error_str or "Too Many Requests" in error_str:
                if verbose:
                    print(
                        f"{Fore.YELLOW}⚠️ Rate limit hit (429). "
                        f"Switching to alternate API key...{Style.RESET_ALL}"
                    )
                
                if not api_key_manager.switch_key():
                    if verbose:
                        print(
                            f"{Fore.RED}❌ No more API keys available. "
                            f"All rate limited.{Style.RESET_ALL}"
                        )
                    return f"Error: Rate limited on all API keys - {error_str}"
            else:
                if verbose:
                    print(f"{Fore.RED}❌ Gemini API error: {error_str}{Style.RESET_ALL}")
                return f"Error: {error_str}"
    
    if last_error:
        return f"Error: {str(last_error)}"
    
    return "Error: Unknown error occurred"
