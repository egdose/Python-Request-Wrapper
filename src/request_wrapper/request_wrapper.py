"""
Main RequestWrapper class for making HTTP requests with retry logic, caching, and proxy support.

This module provides a comprehensive HTTP client wrapper that includes:
- Configurable retry logic for failed requests
- HTTP caching compatible with Scrapy
- Proxy support with rotation capabilities
- Comprehensive error handling
"""

import time
import ssl
import logging
import sys
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urlparse
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import (
    SSLError as RequestsSSLError,
    ProxyError,
    ConnectionError,
    Timeout,
    RequestException,
)

from .cache import Cache
from .exceptions import (
    MaxRetriesExceededError,
    InvalidArgumentError,
    InvalidProxyError,
    SSLError as CustomSSLError,
    CacheError,
)


# Configure default logging
def _setup_default_logging() -> logging.Logger:
    """Set up default logging configuration for RequestWrapper."""
    logger = logging.getLogger('request_wrapper')

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

        # Prevent propagation to root logger to avoid duplicate messages
        logger.propagate = False

    return logger


def configure_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    error_file: Optional[str] = None,
    console_output: bool = True,
    log_format: Optional[str] = None
) -> None:
    """
    Configure logging for RequestWrapper module.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to general log file (e.g., 'logs.log')
        error_file: Path to error-only log file (e.g., 'error.log')
        console_output: Whether to output logs to console/stdout
        log_format: Custom log format string

    Example:
        # Basic file logging
        configure_logging(log_file='logs.log', error_file='error.log')

        # Debug level with custom format
        configure_logging(
            log_level='DEBUG',
            log_file='debug.log',
            log_format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
    """
    logger = logging.getLogger('request_wrapper')

    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Set format
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')

    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Add file handler for general logs
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Add file handler for errors only
    if error_file:
        error_path = Path(error_file)
        error_path.parent.mkdir(parents=True, exist_ok=True)

        error_handler = logging.FileHandler(error_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

    logger.propagate = False
    logger.info(f"Logging configured: level={log_level}, console={console_output}, "
                f"log_file={log_file}, error_file={error_file}")


class RequestWrapper:
    """
    HTTP request wrapper with retry logic, caching, and proxy support.

    This class provides a high-level interface for making HTTP requests with
    built-in retry mechanisms, caching capabilities, and proxy rotation.
    """

    # Default status codes that trigger retries
    DEFAULT_RETRY_STATUS_CODES = {500, 502, 503, 504, 520, 521, 522, 523, 524}

    def __init__(
        self,
        retry_count: int = 3,
        retry_status_codes: Optional[List[int]] = None,
        proxies: Optional[List[Dict[str, str]]] = None,
        cache_enabled: bool = False,
        cache_dir: str = "httpcache",
        cache_compress: bool = False,
        cache_expiry: Optional[int] = None,
        timeout: int = 30,
        user_agent: Optional[str] = None,
        verify_ssl: bool = True,
    ) -> None:
        """
        Initialize the RequestWrapper.

        Args:
            retry_count: Default number of retries for failed requests
            retry_status_codes: List of HTTP status codes that trigger retries
            proxies: List of proxy configurations [{'http': 'proxy1', 'https': 'proxy1'}, ...]
            cache_enabled: Enable/disable request caching
            cache_dir: Directory for storing cached requests
            cache_compress: Compress cached files
            cache_expiry: Cache expiry time in seconds (None = no expiry)
            timeout: Request timeout in seconds
            user_agent: Default User-Agent header
            verify_ssl: Verify SSL certificates
        """
        self.retry_count = self._validate_retry_count(retry_count)
        self.retry_status_codes = set(
            retry_status_codes or self.DEFAULT_RETRY_STATUS_CODES
        )
        self.proxies = self._validate_proxies(proxies or [])
        self.timeout = self._validate_timeout(timeout)
        self.user_agent = user_agent or "RequestWrapper/1.0"
        self.verify_ssl = verify_ssl

        # Initialize cache
        self.cache = Cache(
            cache_dir=cache_dir,
            enabled=cache_enabled,
            compress=cache_compress,
            expiry_time=cache_expiry,
        )

        # Current proxy index for rotation
        self._current_proxy_index = 0

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

        # Set up logging
        self.logger = _setup_default_logging()
        self.logger.info(f"RequestWrapper initialized: retry_count={retry_count}, "
                         f"cache_enabled={cache_enabled}, proxies_count={len(self.proxies)}")

    def _validate_retry_count(self, retry_count: int) -> int:
        """Validate retry count parameter."""
        if not isinstance(retry_count, int) or retry_count < 0:
            raise InvalidArgumentError(
                "retry_count", retry_count, "non-negative integer"
            )
        return retry_count

    def _validate_timeout(self, timeout: Union[int, float]) -> Union[int, float]:
        """Validate timeout parameter."""
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise InvalidArgumentError("timeout", timeout, "positive number")
        return timeout

    def _validate_proxies(self, proxies: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Validate proxy configurations."""
        if not isinstance(proxies, list):
            raise InvalidArgumentError(
                "proxies", proxies, "list of proxy dictionaries")

        validated_proxies = []
        for i, proxy in enumerate(proxies):
            if not isinstance(proxy, dict):
                raise InvalidProxyError(
                    proxy, f"Proxy at index {i} must be a dictionary"
                )

            # Validate proxy format
            for scheme in ["http", "https"]:
                if scheme in proxy:
                    proxy_url = proxy[scheme]
                    try:
                        parsed = urlparse(proxy_url)
                        if not parsed.scheme or not parsed.netloc:
                            raise InvalidProxyError(
                                proxy, f"Invalid proxy URL format: {proxy_url}"
                            )
                    except Exception as e:
                        raise InvalidProxyError(
                            proxy, f"Failed to parse proxy URL: {str(e)}"
                        )

            validated_proxies.append(proxy)

        return validated_proxies

    def add_retry_status_code(self, status_code: int) -> None:
        """
        Add a status code to the retry list.

        Args:
            status_code: HTTP status code to add
        """
        if not isinstance(status_code, int) or not (100 <= status_code <= 599):
            raise InvalidArgumentError(
                "status_code", status_code, "valid HTTP status code (100-599)"
            )
        self.retry_status_codes.add(status_code)
        self.logger.info(f"Added retry status code: {status_code}")

    def remove_retry_status_code(self, status_code: int) -> None:
        """
        Remove a status code from the retry list.

        Args:
            status_code: HTTP status code to remove
        """
        if not isinstance(status_code, int):
            raise InvalidArgumentError("status_code", status_code, "integer")
        self.retry_status_codes.discard(status_code)
        self.logger.info(f"Removed retry status code: {status_code}")

    def get_retry_status_codes(self) -> List[int]:
        """Get current retry status codes."""
        return sorted(list(self.retry_status_codes))

    def _get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get the next proxy from the rotation."""
        if not self.proxies:
            return None

        proxy = self.proxies[self._current_proxy_index]
        self._current_proxy_index = (
            self._current_proxy_index + 1) % len(self.proxies)
        return proxy

    def _should_retry(
        self, response: Optional[requests.Response], exception: Optional[Exception]
    ) -> bool:
        """Determine if a request should be retried."""
        if exception:
            # Retry on connection errors, timeouts, but not SSL errors
            return isinstance(exception, (ConnectionError, Timeout, ProxyError))

        if response and response.status_code in self.retry_status_codes:
            return True

        return False

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        json: Optional[Dict[str, Any]] = None,
        proxy: Optional[Dict[str, str]] = None,
        timeout: Optional[Union[int, float]] = None,
        verify_ssl: Optional[bool] = None,
        use_cache: Optional[bool] = None,
    ) -> requests.Response:
        """
        Make a single HTTP request with all the configured options.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Target URL
            params: URL parameters to append to the URL
            headers: Request headers
            data: Request body data
            json: JSON data to send
            proxy: Proxy configuration for this request
            timeout: Request timeout
            verify_ssl: SSL verification for this request
            use_cache: Whether to use cache for this request

        Returns:
            Response object

        Raises:
            Various exceptions based on request failure type
        """
        # Prepare request parameters
        headers = headers or {}
        timeout = timeout or self.timeout
        verify_ssl = verify_ssl if verify_ssl is not None else self.verify_ssl
        use_cache = use_cache if use_cache is not None else self.cache.enabled

        # Convert data to bytes for caching
        body_bytes = b""
        if data:
            if isinstance(data, str):
                body_bytes = data.encode("utf-8")
            elif isinstance(data, bytes):
                body_bytes = data
            elif isinstance(data, dict):
                import urllib.parse

                body_bytes = urllib.parse.urlencode(data).encode("utf-8")
        elif json:
            import json as json_lib

            body_bytes = json_lib.dumps(json).encode("utf-8")

        # Check cache first
        if use_cache and method.upper() in ["GET", "HEAD"]:
            path_str = []
            cached_response = self.cache.get(
                method, url, headers, body_bytes, params, cache_hit_path=path_str)
            if cached_response:
                self.logger.debug(f"Cache hit for {method} {url}")
                if len(path_str) > 0:
                    self.logger.info(f"{url} - cache hit -> {path_str[0]}")
                return cached_response

        self.logger.debug(
            f"Making {method} request to {url} (cache: {'enabled' if use_cache else 'disabled'})")

        # Prepare request kwargs
        request_kwargs = {
            "headers": headers,
            "timeout": timeout,
            "verify": verify_ssl,
            "proxies": proxy,
        }

        if params is not None:
            request_kwargs["params"] = params
        if data is not None:
            request_kwargs["data"] = data
        if json is not None:
            request_kwargs["json"] = json

        try:
            # Make the request
            self.logger.debug(
                f"Sending {method} request to {url} with timeout={timeout}")
            response = self.session.request(method, url, **request_kwargs)

            self.logger.info(
                f"{method} {url} -> {response.status_code} ({len(response.content)} bytes)")

            # Cache successful responses
            if use_cache and response.status_code < 400:
                try:
                    self.cache.store(method, url, response,
                                     headers, body_bytes, params)
                    self.logger.debug(f"Response cached for {method} {url}")
                except CacheError as e:
                    # Don't fail the request if caching fails
                    self.logger.warning(
                        f"Failed to cache response for {method} {url}: {e}")
                    pass

            return response

        except RequestsSSLError as e:
            raise CustomSSLError(url, e)
        except Exception as e:
            raise e

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        json: Optional[Dict[str, Any]] = None,
        retry_count: Optional[int] = None,
        proxy: Optional[Dict[str, str]] = None,
        timeout: Optional[Union[int, float]] = None,
        verify_ssl: Optional[bool] = None,
        use_cache: Optional[bool] = None,
    ) -> requests.Response:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Target URL
            params: URL parameters to append to the URL
            headers: Request headers
            data: Request body data
            json: JSON data to send
            retry_count: Number of retries for this request (overrides default)
            proxy: Proxy configuration (overrides default rotation)
            timeout: Request timeout (overrides default)
            verify_ssl: SSL verification (overrides default)
            use_cache: Whether to use cache (overrides default)

        Returns:
            Response object

        Raises:
            MaxRetriesExceededError: When max retries exceeded
            CustomSSLError: On SSL-related errors
            InvalidArgumentError: On invalid parameters
            Other request-related exceptions
        """
        # Validate method
        if not isinstance(method, str) or not method.strip():
            raise InvalidArgumentError("method", method, "non-empty string")

        # Validate URL
        if not isinstance(url, str) or not url.strip():
            raise InvalidArgumentError("url", url, "non-empty string")

        method = method.upper()
        retry_count = retry_count if retry_count is not None else self.retry_count

        last_response = None
        last_exception = None

        self.logger.info(
            f"Starting {method} request to {url} (max_retries={retry_count})")

        for attempt in range(retry_count + 1):
            try:
                # Use provided proxy or get next from rotation
                current_proxy = proxy or self._get_next_proxy()
                if current_proxy:
                    self.logger.debug(f"Using proxy: {current_proxy}")

                response = self._make_request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    data=data,
                    json=json,
                    proxy=current_proxy,
                    timeout=timeout,
                    verify_ssl=verify_ssl,
                    use_cache=use_cache,
                )

                # Check if we should retry based on status code
                if not self._should_retry(response, None):
                    if attempt > 0:
                        self.logger.info(
                            f"Request succeeded after {attempt} retries")
                    return response

                last_response = response
                self.logger.warning(f"Request failed with status {response.status_code}, "
                                    f"attempt {attempt + 1}/{retry_count + 1}")

            except Exception as e:
                last_exception = e
                self.logger.warning(f"Request failed with exception: {type(e).__name__}: {e}, "
                                    f"attempt {attempt + 1}/{retry_count + 1}")

                # Don't retry SSL errors
                if isinstance(e, CustomSSLError):
                    self.logger.error(f"SSL error occurred, not retrying: {e}")
                    raise e

                # Check if we should retry based on exception type
                if not self._should_retry(None, e):
                    self.logger.error(
                        f"Non-retryable exception occurred: {type(e).__name__}: {e}")
                    raise e

            # Wait before retry (simple backoff)
            if attempt < retry_count:
                # Exponential backoff, max 10 seconds
                sleep_time = min(2**attempt, 10)
                self.logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)

        # All retries exhausted
        self.logger.error(f"All retries exhausted for {method} {url} "
                          f"(last_status={last_response.status_code if last_response else 'None'}, "
                          f"last_error={type(last_exception).__name__ if last_exception else 'None'})")
        raise MaxRetriesExceededError(
            url=url,
            max_retries=retry_count,
            last_status_code=last_response.status_code if last_response else None,
            last_error=last_exception,
        )

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_count: Optional[int] = None,
        proxy: Optional[Dict[str, str]] = None,
        timeout: Optional[Union[int, float]] = None,
        verify_ssl: Optional[bool] = None,
        use_cache: Optional[bool] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Make a GET request.

        Args:
            url: Target URL
            params: URL parameters to append to the URL
            headers: Request headers
            retry_count: Number of retries (overrides default)
            proxy: Proxy configuration (overrides default)
            timeout: Request timeout (overrides default)
            verify_ssl: SSL verification (overrides default)
            use_cache: Whether to use cache (overrides default)
            **kwargs: Additional arguments passed to requests

        Returns:
            Response object
        """
        return self.request(
            method="GET",
            url=url,
            params=params,
            headers=headers,
            retry_count=retry_count,
            proxy=proxy,
            timeout=timeout,
            verify_ssl=verify_ssl,
            use_cache=use_cache,
            **kwargs,
        )

    def post(
        self,
        url: str,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_count: Optional[int] = None,
        proxy: Optional[Dict[str, str]] = None,
        timeout: Optional[Union[int, float]] = None,
        verify_ssl: Optional[bool] = None,
        use_cache: Optional[bool] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Make a POST request.

        Args:
            url: Target URL
            data: Request body data
            json: JSON data to send
            headers: Request headers
            retry_count: Number of retries (overrides default)
            proxy: Proxy configuration (overrides default)
            timeout: Request timeout (overrides default)
            verify_ssl: SSL verification (overrides default)
            use_cache: Whether to use cache (overrides default)
            **kwargs: Additional arguments passed to requests

        Returns:
            Response object
        """
        return self.request(
            method="POST",
            url=url,
            data=data,
            json=json,
            headers=headers,
            retry_count=retry_count,
            proxy=proxy,
            timeout=timeout,
            verify_ssl=verify_ssl,
            use_cache=use_cache,
            **kwargs,
        )

    def clear_cache(self) -> None:
        """Clear all cached requests."""
        cache_size = self.cache.size()
        self.cache.clear()
        self.logger.info(f"Cache cleared ({cache_size} items removed)")

    def get_cache_size(self) -> int:
        """Get the number of items in cache."""
        return self.cache.size()

    def close(self) -> None:
        """Close the underlying session."""
        self.session.close()
        self.logger.info("RequestWrapper session closed")

    def __enter__(self) -> 'RequestWrapper':
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager and close the session."""
        self.close()
