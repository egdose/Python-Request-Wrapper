"""
Basic tests for the RequestWrapper module.
"""

import pytest
from unittest.mock import Mock, patch
from request_wrapper import (
    RequestWrapper,
    Cache,
    MaxRetriesExceededError,
    InvalidArgumentError,
    InvalidProxyError,
    SSLError,
    CacheError,
)


class TestRequestWrapper:
    """Test cases for RequestWrapper class."""

    def test_init_default_values(self):
        """Test RequestWrapper initialization with default values."""
        client = RequestWrapper()

        assert client.retry_count == 3
        assert 500 in client.retry_status_codes
        assert client.proxies == []
        assert client.timeout == 30
        assert client.user_agent == "RequestWrapper/1.0"
        assert client.verify_ssl is True
        assert client.cache.enabled is False

    def test_init_custom_values(self):
        """Test RequestWrapper initialization with custom values."""
        proxies = [{"http": "http://proxy:8080"}]
        client = RequestWrapper(
            retry_count=5,
            retry_status_codes=[400, 500],
            proxies=proxies,
            cache_enabled=True,
            timeout=60,
            verify_ssl=False,
        )

        assert client.retry_count == 5
        assert client.retry_status_codes == {400, 500}
        assert client.proxies == proxies
        assert client.timeout == 60
        assert client.verify_ssl is False
        assert client.cache.enabled is True

    def test_invalid_retry_count(self):
        """Test validation of retry_count parameter."""
        with pytest.raises(InvalidArgumentError):
            RequestWrapper(retry_count=-1)

        with pytest.raises(InvalidArgumentError):
            RequestWrapper(retry_count="invalid")

    def test_invalid_timeout(self):
        """Test validation of timeout parameter."""
        with pytest.raises(InvalidArgumentError):
            RequestWrapper(timeout=0)

        with pytest.raises(InvalidArgumentError):
            RequestWrapper(timeout=-5)

    def test_invalid_proxies(self):
        """Test validation of proxies parameter."""
        with pytest.raises(InvalidArgumentError):
            RequestWrapper(proxies="invalid")

        with pytest.raises(InvalidProxyError):
            RequestWrapper(proxies=["invalid_proxy"])

        with pytest.raises(InvalidProxyError):
            RequestWrapper(proxies=[{"http": "invalid_url"}])

    def test_add_retry_status_code(self):
        """Test adding retry status codes."""
        client = RequestWrapper()
        initial_count = len(client.retry_status_codes)

        client.add_retry_status_code(429)
        assert 429 in client.retry_status_codes
        assert len(client.retry_status_codes) == initial_count + 1

    def test_remove_retry_status_code(self):
        """Test removing retry status codes."""
        client = RequestWrapper()
        client.add_retry_status_code(429)

        client.remove_retry_status_code(429)
        assert 429 not in client.retry_status_codes

    def test_get_retry_status_codes(self):
        """Test getting retry status codes."""
        client = RequestWrapper(retry_status_codes=[500, 502, 429])
        codes = client.get_retry_status_codes()

        assert isinstance(codes, list)
        assert sorted(codes) == [429, 500, 502]

    @patch("request_wrapper.request_wrapper.requests.Session.request")
    def test_successful_request(self, mock_request):
        """Test successful HTTP request."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test content"
        mock_request.return_value = mock_response

        client = RequestWrapper()
        response = client.get("https://example.com")

        assert response.status_code == 200
        mock_request.assert_called_once()

    def test_invalid_method(self):
        """Test request with invalid method."""
        client = RequestWrapper()

        with pytest.raises(InvalidArgumentError):
            client.request("", "https://example.com")

    def test_invalid_url(self):
        """Test request with invalid URL."""
        client = RequestWrapper()

        with pytest.raises(InvalidArgumentError):
            client.request("GET", "")


class TestCache:
    """Test cases for Cache class."""

    def test_init_default_values(self):
        """Test Cache initialization with default values."""
        cache = Cache()

        assert cache.cache_dir.name == "httpcache"
        assert cache.enabled is True
        assert cache.compress is False
        assert cache.expiry_time is None

    def test_init_custom_values(self):
        """Test Cache initialization with custom values."""
        cache = Cache(
            cache_dir="custom_cache", enabled=False, compress=True, expiry_time=3600
        )

        assert cache.cache_dir.name == "custom_cache"
        assert cache.enabled is False
        assert cache.compress is True
        assert cache.expiry_time == 3600

    def test_request_hash_generation(self):
        """Test request hash generation."""
        cache = Cache()

        hash1 = cache._get_request_hash("GET", "https://example.com", {}, b"")
        hash2 = cache._get_request_hash("GET", "https://example.com", {}, b"")
        hash3 = cache._get_request_hash("POST", "https://example.com", {}, b"")

        # Same requests should have same hash
        assert hash1 == hash2

        # Different methods should have different hash
        assert hash1 != hash3

    def test_cache_disabled(self):
        """Test cache behavior when disabled."""
        cache = Cache(enabled=False)

        # Should return None for disabled cache
        result = cache.get("GET", "https://example.com")
        assert result is None

        # Store should do nothing when disabled
        mock_response = Mock()
        cache.store("GET", "https://example.com", mock_response)
        # Should not raise any errors


class TestExceptions:
    """Test cases for custom exceptions."""

    def test_max_retries_exceeded_error(self):
        """Test MaxRetriesExceededError exception."""
        error = MaxRetriesExceededError(
            url="https://example.com",
            max_retries=3,
            last_status_code=500,
            last_error=Exception("test error"),
        )

        assert error.url == "https://example.com"
        assert error.max_retries == 3
        assert error.last_status_code == 500
        assert isinstance(error.last_error, Exception)
        assert "Maximum retries (3) exceeded" in str(error)

    def test_invalid_argument_error(self):
        """Test InvalidArgumentError exception."""
        error = InvalidArgumentError(
            argument_name="test_arg", argument_value="invalid", expected="integer"
        )

        assert error.argument_name == "test_arg"
        assert error.argument_value == "invalid"
        assert error.expected == "integer"
        assert "Invalid argument 'test_arg'" in str(error)

    def test_invalid_proxy_error(self):
        """Test InvalidProxyError exception."""
        error = InvalidProxyError(proxy={"invalid": "proxy"}, reason="Invalid format")

        assert error.proxy == {"invalid": "proxy"}
        assert error.reason == "Invalid format"
        assert "Invalid proxy configuration" in str(error)

    def test_ssl_error(self):
        """Test SSLError exception."""
        original_error = Exception("SSL handshake failed")
        error = SSLError(url="https://example.com", ssl_error=original_error)

        assert error.url == "https://example.com"
        assert error.ssl_error == original_error
        assert "SSL error occurred while requesting" in str(error)

    def test_cache_error(self):
        """Test CacheError exception."""
        error = CacheError(
            operation="write", reason="Permission denied", cache_dir="/tmp/cache"
        )

        assert error.operation == "write"
        assert error.reason == "Permission denied"
        assert error.cache_dir == "/tmp/cache"
        assert "Cache write operation failed" in str(error)


if __name__ == "__main__":
    pytest.main([__file__])
