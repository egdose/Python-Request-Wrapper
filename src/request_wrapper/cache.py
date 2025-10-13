"""
HTTP cache implementation compatible with Scrapy's caching format.

This module provides a caching system that stores HTTP requests and responses
in a format similar to Scrapy's HttpCacheMiddleware, allowing for efficient
request caching and replay.
"""

import hashlib
import json
import os
import pickle
import time
import gzip
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlparse

import requests

from .exceptions import CacheError


class Cache:
    """
    HTTP cache that stores requests and responses in Scrapy-compatible format.

    The cache stores each request/response pair in a separate directory named
    by the request's hash. Each cached item contains:
    - request_body: The original request data
    - request_headers: The request headers
    - response_body: The response content
    - response_headers: The response headers
    - meta: Metadata about the cached item
    """

    def __init__(
        self,
        cache_dir: str = "httpcache",
        enabled: bool = True,
        compress: bool = False,
        expiry_time: Optional[int] = None,
    ) -> None:
        """
        Initialize the cache.

        Args:
            cache_dir: Directory to store cache files (default: "httpcache")
            enabled: Whether caching is enabled (default: True)
            compress: Whether to compress cached files (default: False)
            expiry_time: Cache expiry time in seconds (None = no expiry)
        """
        self.cache_dir = Path(cache_dir)
        self.enabled = enabled
        self.compress = compress
        self.expiry_time = expiry_time

        if self.enabled:
            self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise CacheError(
                "create",
                f"Failed to create cache directory: {str(e)}",
                str(self.cache_dir),
            )

    def _get_request_hash(
        self, method: str, url: str, headers: Dict[str, str], body: bytes, params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a unique hash for the request.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            params: URL parameters

        Returns:
            Hexadecimal hash string
        """
        # Create a normalized representation for hashing
        hash_data = {
            "method": method.upper(),
            "url": url,
            "headers": dict(sorted(headers.items())),
            "body": body.hex() if body else "",
            "params": dict(sorted(params.items())) if params else {},
        }

        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_string.encode("utf-8")).hexdigest()

    def _get_cache_path(self, request_hash: str) -> Path:
        """Get the cache directory path for a request hash."""
        return self.cache_dir / request_hash

    def _write_file(self, file_path: Path, data: bytes) -> None:
        """Write data to file, optionally compressed."""
        try:
            if self.compress:
                with gzip.open(file_path, "wb") as f:
                    f.write(data)
            else:
                with open(file_path, "wb") as f:
                    f.write(data)
        except OSError as e:
            raise CacheError(
                "write",
                f"Failed to write cache file {file_path}: {str(e)}",
                str(self.cache_dir),
            )

    def _read_file(self, file_path: Path) -> bytes:
        """Read data from file, handling compression."""
        try:
            if self.compress and file_path.suffix == ".gz":
                with gzip.open(file_path, "rb") as f:
                    return f.read()
            else:
                with open(file_path, "rb") as f:
                    return f.read()
        except OSError as e:
            raise CacheError(
                "read",
                f"Failed to read cache file {file_path}: {str(e)}",
                str(self.cache_dir),
            )

    def _is_expired(self, cache_path: Path) -> bool:
        """Check if cached item has expired."""
        if self.expiry_time is None:
            return False

        try:
            meta_file = cache_path / "meta"
            if not meta_file.exists():
                return True

            with open(meta_file, "r") as f:
                meta = json.load(f)

            cached_time = meta.get("timestamp", 0)
            return (time.time() - cached_time) > self.expiry_time

        except (OSError, json.JSONDecodeError):
            return True

    def get(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None,
        params: Optional[Dict[str, Any]] = None,
        cache_hit_path: Optional[List[str]] = None,
    ) -> Optional[requests.Response]:
        """
        Get cached response for a request.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            params: URL parameters

        Returns:
            Cached Response object or None if not found/expired
        """
        if not self.enabled:
            return None

        headers = headers or {}
        body = body or b""
        params = params or {}

        request_hash = self._get_request_hash(
            method, url, headers, body, params)
        cache_path = self._get_cache_path(request_hash)

        if not cache_path.exists() or self._is_expired(cache_path):
            return None

        try:
            # Read cached response data
            response_body_file = cache_path / "response_body"
            response_headers_file = cache_path / "response_headers"
            meta_file = cache_path / "meta"

            if not all(
                f.exists()
                for f in [response_body_file, response_headers_file, meta_file]
            ):
                return None

            response_body = self._read_file(response_body_file)

            with open(response_headers_file, "r") as f:
                response_headers = json.load(f)

            with open(meta_file, "r") as f:
                meta = json.load(f)

            # Create a mock response object
            response = requests.Response()
            response._content = response_body
            response.headers.update(response_headers)
            response.status_code = meta.get("status_code", 200)
            response.reason = meta.get("reason", "OK")
            response.url = url

            # For logging output path
            if cache_hit_path is not None and isinstance(cache_hit_path, list):
                cache_hit_path.append(str(response_body_file.absolute()))

            return response

        except (OSError, json.JSONDecodeError) as e:
            raise CacheError(
                "read", f"Failed to read cached response: {str(e)}", str(
                    self.cache_dir)
            )

    def store(
        self,
        method: str,
        url: str,
        response: requests.Response,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Store response in cache.

        Args:
            method: HTTP method
            url: Request URL
            response: Response object to cache
            headers: Request headers
            body: Request body
            params: URL parameters
        """
        if not self.enabled:
            return

        headers = headers or {}
        body = body or b""
        params = params or {}

        request_hash = self._get_request_hash(
            method, url, headers, body, params)
        cache_path = self._get_cache_path(request_hash)

        try:
            cache_path.mkdir(parents=True, exist_ok=True)

            # Store request data
            request_body_file = cache_path / "request_body"
            request_headers_file = cache_path / "request_headers"

            self._write_file(request_body_file, body)

            with open(request_headers_file, "w") as f:
                json.dump(dict(headers), f)

            # Store response data
            response_body_file = cache_path / "response_body"
            response_headers_file = cache_path / "response_headers"

            if self.compress:
                response_body_file = response_body_file.with_suffix(".gz")

            self._write_file(response_body_file, response.content)

            with open(response_headers_file, "w") as f:
                json.dump(dict(response.headers), f)

            # Store metadata
            meta = {
                "timestamp": time.time(),
                "method": method.upper(),
                "url": url,
                "status_code": response.status_code,
                "reason": response.reason,
            }

            with open(cache_path / "meta", "w") as f:
                json.dump(meta, f)

        except OSError as e:
            raise CacheError(
                "write",
                f"Failed to store response in cache: {str(e)}",
                str(self.cache_dir),
            )

    def clear(self) -> None:
        """Clear all cached items."""
        if not self.enabled or not self.cache_dir.exists():
            return

        try:
            import shutil

            shutil.rmtree(self.cache_dir)
            self._ensure_cache_dir()
        except OSError as e:
            raise CacheError(
                "clear", f"Failed to clear cache: {str(e)}", str(
                    self.cache_dir)
            )

    def delete(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Delete specific cached item.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            params: URL parameters

        Returns:
            True if item was deleted, False if it didn't exist
        """
        if not self.enabled:
            return False

        headers = headers or {}
        body = body or b""
        params = params or {}

        request_hash = self._get_request_hash(
            method, url, headers, body, params)
        cache_path = self._get_cache_path(request_hash)

        if not cache_path.exists():
            return False

        try:
            import shutil

            shutil.rmtree(cache_path)
            return True
        except OSError as e:
            raise CacheError(
                "delete", f"Failed to delete cached item: {str(e)}", str(
                    self.cache_dir)
            )

    def size(self) -> int:
        """Get the number of cached items."""
        if not self.enabled or not self.cache_dir.exists():
            return 0

        try:
            return len([d for d in self.cache_dir.iterdir() if d.is_dir()])
        except OSError:
            return 0
