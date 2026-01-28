"""Rate limiting configuration for DocuQuery API."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create rate limiter instance
limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations
RATE_LIMITS = {
    "upload": "10/minute",  # 10 uploads per minute
    "query": "30/minute",  # 30 queries per minute
    "default": "100/minute",  # 100 requests per minute default
}
