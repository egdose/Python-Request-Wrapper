"""
RequestWrapper - A HTTP request wrapper with retry logic, caching, and proxy support.

This package provides a comprehensive HTTP client that includes:
- Configurable retry logic for failed requests
- HTTP caching compatible with Scrapy format
- Proxy support with rotation capabilities
- Comprehensive error handling with custom exceptions

Main Classes:
    RequestWrapper: The main HTTP client class
    Cache: HTTP caching system

Exception Classes:
    RequestWrapperError: Base exception
    MaxRetriesExceededError: Raised when max retries exceeded
    InvalidArgumentError: Raised for invalid function arguments
    InvalidProxyError: Raised for invalid proxy configurations
    SSLError: Raised for SSL-related errors
    CacheError: Raised for cache-related errors

Example:
    Basic usage with retry logic:

    >>> from request_wrapper import RequestWrapper
    >>> client = RequestWrapper(retry_count=3, cache_enabled=True)
    >>> response = client.get('https://api.example.com/data')
    >>> print(response.status_code)

    With custom retry status codes and proxies:

    >>> proxies = [
    ...     {'http': 'http://proxy1:8080', 'https': 'http://proxy1:8080'},
    ...     {'http': 'http://proxy2:8080', 'https': 'http://proxy2:8080'}
    ... ]
    >>> client = RequestWrapper(
    ...     retry_count=5,
    ...     proxies=proxies,
    ...     cache_enabled=True,
    ...     cache_dir="my_cache"
    ... )
    >>> client.add_retry_status_code(429)  # Add rate limit status
    >>> response = client.post('https://api.example.com/submit', json={'data': 'value'})
"""

from .request_wrapper import RequestWrapper, configure_logging
from .cache import Cache
from .exceptions import (
    RequestWrapperError,
    MaxRetriesExceededError,
    InvalidArgumentError,
    InvalidProxyError,
    SSLError,
    CacheError,
)

__version__ = "0.1.0"
__author__ = "Ubaid Ullah"
__email__ = "ubaidullah0504@gmail.com"

__all__ = [
    "RequestWrapper",
    "Cache",
    "configure_logging",
    "RequestWrapperError",
    "MaxRetriesExceededError",
    "InvalidArgumentError",
    "InvalidProxyError",
    "SSLError",
    "CacheError",
]
