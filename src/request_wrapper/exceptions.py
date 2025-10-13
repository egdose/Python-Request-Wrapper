"""
Custom exceptions for the request_wrapper module.

This module defines specific exception classes for different error conditions
that can occur during HTTP request processing.
"""

from typing import Optional, Any


class RequestWrapperError(Exception):
    """Base exception class for all request_wrapper related errors."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message
            details: Optional additional details about the error
        """
        self.message = message
        self.details = details
        super().__init__(self.message)


class MaxRetriesExceededError(RequestWrapperError):
    """Raised when the maximum number of retries has been exceeded."""

    def __init__(
        self,
        url: str,
        max_retries: int,
        last_status_code: Optional[int] = None,
        last_error: Optional[Exception] = None,
    ) -> None:
        """Initialize the exception.

        Args:
            url: The URL that failed after max retries
            max_retries: The maximum number of retries that were attempted
            last_status_code: The last HTTP status code received, if any
            last_error: The last exception that occurred, if any
        """
        self.url = url
        self.max_retries = max_retries
        self.last_status_code = last_status_code
        self.last_error = last_error

        message = f"Maximum retries ({max_retries}) exceeded for URL: {url}"
        if last_status_code:
            message += f" (last status: {last_status_code})"
        if last_error:
            message += f" (last error: {str(last_error)})"

        super().__init__(
            message,
            {
                "url": url,
                "max_retries": max_retries,
                "last_status_code": last_status_code,
                "last_error": last_error,
            },
        )


class InvalidArgumentError(RequestWrapperError):
    """Raised when invalid arguments are passed to methods."""

    def __init__(self, argument_name: str, argument_value: Any, expected: str) -> None:
        """Initialize the exception.

        Args:
            argument_name: Name of the invalid argument
            argument_value: The invalid value that was provided
            expected: Description of what was expected
        """
        self.argument_name = argument_name
        self.argument_value = argument_value
        self.expected = expected

        message = (
            f"Invalid argument '{argument_name}': got {type(argument_value).__name__} "
            f"({argument_value}), expected {expected}"
        )

        super().__init__(
            message,
            {
                "argument_name": argument_name,
                "argument_value": argument_value,
                "expected": expected,
            },
        )


class InvalidProxyError(RequestWrapperError):
    """Raised when an invalid proxy configuration is provided."""

    def __init__(self, proxy: Any, reason: str) -> None:
        """Initialize the exception.

        Args:
            proxy: The invalid proxy configuration
            reason: Explanation of why the proxy is invalid
        """
        self.proxy = proxy
        self.reason = reason

        message = f"Invalid proxy configuration: {reason}. Proxy: {proxy}"

        super().__init__(message, {"proxy": proxy, "reason": reason})


class SSLError(RequestWrapperError):
    """Raised when SSL/TLS related errors occur during requests."""

    def __init__(self, url: str, ssl_error: Exception) -> None:
        """Initialize the exception.

        Args:
            url: The URL where the SSL error occurred
            ssl_error: The original SSL exception
        """
        self.url = url
        self.ssl_error = ssl_error

        message = f"SSL error occurred while requesting {url}: {str(ssl_error)}"

        super().__init__(message, {"url": url, "ssl_error": ssl_error})


class CacheError(RequestWrapperError):
    """Raised when cache-related operations fail."""

    def __init__(
        self, operation: str, reason: str, cache_dir: Optional[str] = None
    ) -> None:
        """Initialize the exception.

        Args:
            operation: The cache operation that failed (e.g., 'read', 'write', 'delete')
            reason: Explanation of why the operation failed
            cache_dir: The cache directory involved, if applicable
        """
        self.operation = operation
        self.reason = reason
        self.cache_dir = cache_dir

        message = f"Cache {operation} operation failed: {reason}"
        if cache_dir:
            message += f" (cache dir: {cache_dir})"

        super().__init__(
            message, {"operation": operation, "reason": reason, "cache_dir": cache_dir}
        )
