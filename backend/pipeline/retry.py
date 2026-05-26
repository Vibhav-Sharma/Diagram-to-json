"""
Gemini API Retry Utility
========================
Provides retry logic with exponential backoff for Gemini API calls.
Handles 503 UNAVAILABLE, timeouts, and transient errors gracefully.
"""

import time
import json
from functools import wraps


# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 2.0    # seconds
MAX_DELAY = 15.0    # seconds
BACKOFF_FACTOR = 2  # exponential backoff multiplier

# Errors that are retryable (transient)
RETRYABLE_KEYWORDS = [
    "503", "UNAVAILABLE", "overloaded", "timeout",
    "RESOURCE_EXHAUSTED", "rate limit", "quota",
    "DEADLINE_EXCEEDED", "internal error", "500",
]


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is transient and worth retrying."""
    error_str = str(error).lower()
    return any(keyword.lower() in error_str for keyword in RETRYABLE_KEYWORDS)


def gemini_retry(func):
    """
    Decorator that adds retry logic with exponential backoff to Gemini API calls.
    
    - Retries up to MAX_RETRIES times on transient errors (503, timeout, etc.)
    - Uses exponential backoff between retries
    - Non-retryable errors (400 bad request, schema errors) are raised immediately
    
    Usage:
        @gemini_retry
        def my_api_call(client, ...):
            response = client.models.generate_content(...)
            return json.loads(response.text)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        last_error = None
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if not is_retryable_error(e):
                    # Non-retryable error — fail immediately
                    raise
                
                if attempt < MAX_RETRIES:
                    delay = min(BASE_DELAY * (BACKOFF_FACTOR ** (attempt - 1)), MAX_DELAY)
                    print(f"[Retry] {func.__name__} attempt {attempt}/{MAX_RETRIES} failed: {e}")
                    print(f"[Retry] Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    print(f"[Retry] {func.__name__} all {MAX_RETRIES} attempts failed.")
        
        # All retries exhausted — raise the last error
        raise last_error
    
    return wrapper


def make_eval_failure(reason: str, error: Exception) -> dict:
    """
    Create a standardized evaluation failure result.
    This is returned INSTEAD of a fake 0/10 score when the API fails.
    
    The frontend uses the 'status' field to distinguish between:
    - A real evaluation (status absent or 'success')
    - A temporary failure (status = 'evaluation_failed')
    """
    return {
        "status": "evaluation_failed",
        "reason": reason,
        "error": str(error),
        "retry_exhausted": True,
    }
