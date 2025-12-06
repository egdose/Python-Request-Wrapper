# RequestWrapper

A Python HTTP request wrapper with retry logic, caching, and proxy support.

## Disclaimer

**This project was created for personal use and is made public for convenience in installation via GitHub.** The code was developed with the assistance of AI coding tools (GitHub Copilot) to quickly implement functionality. While this code is shared publicly:

- **No Ownership Claims**: I do not claim exclusive ownership or originality of all code patterns and implementations
- **Use At Your Own Risk**: This software is provided "as is" without warranty of any kind
- **No Responsibility**: I am not responsible if similar code exists elsewhere or for any issues arising from its use
- **MIT Licensed**: Feel free to use, modify, or distribute this code under the MIT License terms
- **Copyright Issues**: If you believe there is a copyright violation or any concerns, please open an issue and I will address it promptly

This is a learning project and personal tool - use it if you find it helpful, but understand the above limitations.

## Features

- **Retry Logic**: Configurable retry mechanism with exponential backoff for failed requests
- **HTTP Caching**: Scrapy-compatible caching system with optional compression
- **Proxy Support**: Built-in proxy rotation and configuration
- **SSL Handling**: Custom SSL certificate support for proxies, with proper error handling and verification options
- **Cookie Management**: Support for default cookies and per-request cookie customization
- **Type Safety**: Full type hints for better IDE support and code reliability
- **Error Handling**: Custom exceptions for different error conditions
- **Easy Configuration**: Simple constructor-based configuration with sensible defaults

## Installation

### From GitHub (Recommended)

Install directly from GitHub:

```bash
pip install git+https://github.com/egdose/Python-Request-Wrapper.git
```

For development with extra tools:

```bash
pip install "git+https://github.com/egdose/Python-Request-Wrapper.git#egg=request-wrapper[dev]"
```

### From Local Source

If you've cloned the repository:

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick Start

### Basic Usage

```python
from request_wrapper import RequestWrapper

# Create a client with default settings
client = RequestWrapper()

# Make a simple GET request (default - only returns response)
response = client.get('https://api.example.com/data')
print(f"Status: {response.status_code}")
print(f"Content: {response.text}")

# Make a POST request with JSON data
response = client.post(
    'https://api.example.com/submit',
    json={'name': 'John', 'age': 30}
)
```

### With Retry Configuration

```python
client = RequestWrapper(
    retry_count=5,                    # Retry up to 5 times
    retry_status_codes=[500, 502, 503, 504, 429]  # Custom retry status codes
)

# This request will be retried on 5xx errors and rate limits
response = client.get('https://unreliable-api.example.com/data')
```

### With Caching

```python
client = RequestWrapper(
    cache_enabled=True,               # Enable caching
    cache_dir="my_cache",            # Custom cache directory
    cache_compress=True,             # Compress cache files
    cache_expiry=3600               # Cache expires after 1 hour
)

# Default usage - only get response
response1 = client.get('https://api.example.com/data')

# To check if response came from cache, use return_cache_info=True
response2, cache_hit = client.get('https://api.example.com/data', return_cache_info=True)
print(f"From cache: {cache_hit}")  # True
```

### With Proxy Rotation

```python
proxies = [
    {'http': 'http://proxy1:8080', 'https': 'http://proxy1:8080'},
    {'http': 'http://proxy2:8080', 'https': 'http://proxy2:8080'},
    {'http': 'http://proxy3:8080', 'https': 'http://proxy3:8080'}
]

client = RequestWrapper(
    proxies=proxies,                 # Proxy list for rotation
    retry_count=3
)

# Requests will rotate through the proxy list
response = client.get('https://api.example.com/data')
```

### With Custom SSL Certificate

When using proxies that require custom SSL certificates, you can provide a path to your `.crt` file:

```python
# Use custom SSL certificate for all requests
client = RequestWrapper(
    proxies=proxies,
    ssl_cert_path='path/to/certificate.crt'  # Path to your SSL certificate
)

# Now all requests will use your custom certificate for SSL verification
response = client.get('https://api.example.com/data')

# You can also override SSL verification per-request
response = client.get(
    'https://api.example.com/data',
    verify_ssl='path/to/another/cert.crt'  # Use different cert for this request
)

# Or disable SSL verification for specific requests (not recommended for production)
response = client.get(
    'https://api.example.com/data',
    verify_ssl=False
)
```

**Use Case Example - Corporate Proxy:**

```python
# When your corporate proxy uses a custom SSL certificate
proxies = [{'http': 'http://corporate-proxy:8080', 'https': 'https://corporate-proxy:8080'}]

client = RequestWrapper(
    proxies=proxies,
    ssl_cert_path='corporate_proxy_ca.crt',  # Corporate CA certificate
    retry_count=3
)

# No SSL errors or warnings!
response = client.get('https://internal-api.company.com/data')
```

### With Cookies

You can set default cookies for all requests or provide them per-request:

```python
# Set default cookies for all requests
client = RequestWrapper(
    cookies={'session_id': 'abc123', 'user_pref': 'dark_mode'}
)

# All requests will include these cookies
response = client.get('https://api.example.com/data')

# Add additional cookies for a specific request (merges with default)
response = client.get(
    'https://api.example.com/user/profile',
    cookies={'auth_token': 'xyz789'}  # Merged with default cookies
)

# Only use specific cookies for a request (still merges with default)
response = client.post(
    'https://api.example.com/submit',
    json={'key': 'value'},
    cookies={'csrf_token': 'token123'}
)
```

**Authentication Example:**

```python
# Maintain session with cookies
client = RequestWrapper(
    cookies={
        'session_id': 'your_session_id',
        'auth_token': 'your_auth_token'
    }
)

# All subsequent requests will include these cookies
response = client.get('https://api.example.com/protected/resource')
user_data = client.get('https://api.example.com/user/data')
```

## Advanced Usage

### Custom Retry Status Codes

```python
client = RequestWrapper()

# Add custom status codes to retry list
client.add_retry_status_code(429)    # Rate limit
client.add_retry_status_code(408)    # Request timeout

# Remove a status code from retry list
client.remove_retry_status_code(500)

# See current retry status codes
print(client.get_retry_status_codes())
```

### Per-Request Configuration

```python
client = RequestWrapper(cache_enabled=True, proxies=proxies, cookies={'session': 'default'})

# Override settings for specific requests
response = client.get(
    'https://api.example.com/data',
    retry_count=10,                  # Override default retry count
    use_cache=False,                 # Bypass cache for this request
    proxy={'http': 'http://special-proxy:8080'},  # Use specific proxy
    timeout=60,                      # Custom timeout
    verify_ssl=False,                # Disable SSL verification
    cookies={'temp_token': 'xyz'}    # Additional cookies (merged with default)
)
```

### Working with Cache

```python
client = RequestWrapper(cache_enabled=True)

# Make requests (they get cached automatically)
client.get('https://api.example.com/data')
client.get('https://api.example.com/users')

# Check cache size
print(f"Cache contains {client.get_cache_size()} items")

# Clear cache
client.clear_cache()
```

### Logging Configuration

RequestWrapper includes comprehensive logging that helps you monitor requests, retries, caching, and errors.

#### Default Logging (Console Output)

By default, RequestWrapper logs at INFO level to stdout:

```python
from request_wrapper import RequestWrapper

# Default logging - INFO level to console
client = RequestWrapper()
response = client.get('https://api.example.com/data')
# Output: 2024-10-09 14:30:15 - request_wrapper - INFO - RequestWrapper initialized: retry_count=3, cache_enabled=False, proxies_count=0
# Output: 2024-10-09 14:30:15 - request_wrapper - INFO - Starting GET request to https://api.example.com/data (max_retries=3)
# Output: 2024-10-09 14:30:16 - request_wrapper - INFO - GET https://api.example.com/data -> 200 (1234 bytes)
```

#### File Logging Configuration

Configure logging to output to files:

```python
from request_wrapper import configure_logging, RequestWrapper

# Basic file logging
configure_logging(
    log_file='logs.log',        # General logs
    error_file='error.log'      # Error-only logs
)

# Advanced configuration
configure_logging(
    log_level='DEBUG',          # More detailed logging
    log_file='debug.log',
    error_file='errors.log',
    console_output=True,        # Also keep console output
    log_format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

client = RequestWrapper()
# Now all operations will be logged to files
```

#### Logging Levels

- **DEBUG**: Detailed information (cache hits, proxy usage, request details)
- **INFO**: General information (requests, retries, initialization)
- **WARNING**: Retry attempts, cache failures
- **ERROR**: Failed requests, SSL errors, non-retryable exceptions

#### What Gets Logged

- **Initialization**: Configuration settings
- **Requests**: Method, URL, status code, response size
- **Retries**: Retry attempts, backoff timing, final failures
- **Caching**: Cache hits, cache misses, cache operations
- **Proxies**: Proxy selection and usage
- **Errors**: Exceptions, SSL errors, connection failures

#### Example Log Output

```
2024-10-09 14:30:15 - request_wrapper - INFO - RequestWrapper initialized: retry_count=3, cache_enabled=True, proxies_count=2
2024-10-09 14:30:15 - request_wrapper - INFO - Starting GET request to https://api.example.com/data (max_retries=3)
2024-10-09 14:30:15 - request_wrapper - DEBUG - Using proxy: {'http': 'http://proxy1:8080', 'https': 'http://proxy1:8080'}
2024-10-09 14:30:15 - request_wrapper - DEBUG - Making GET request to https://api.example.com/data (cache: enabled)
2024-10-09 14:30:15 - request_wrapper - DEBUG - Sending GET request to https://api.example.com/data with timeout=30
2024-10-09 14:30:16 - request_wrapper - INFO - GET https://api.example.com/data -> 200 (1234 bytes)
2024-10-09 14:30:16 - request_wrapper - DEBUG - Response cached for GET https://api.example.com/data
```

## Configuration Options

### RequestWrapper Constructor

| Parameter            | Type                     | Default                                       | Description                           |
| -------------------- | ------------------------ | --------------------------------------------- | ------------------------------------- |
| `retry_count`        | int                      | 3                                             | Number of retries for failed requests |
| `retry_status_codes` | List[int]                | [500, 502, 503, 504, 520, 521, 522, 523, 524] | Status codes that trigger retries     |
| `proxies`            | List[Dict]               | []                                            | List of proxy configurations          |
| `cache_enabled`      | bool                     | False                                         | Enable/disable request caching        |
| `cache_dir`          | str                      | "httpcache"                                   | Directory for cache storage           |
| `cache_compress`     | bool                     | False                                         | Compress cached files                 |
| `cache_expiry`       | Optional[int]            | None                                          | Cache expiry in seconds               |
| `timeout`            | int                      | 30                                            | Request timeout in seconds            |
| `user_agent`         | Optional[str]            | "RequestWrapper/1.0"                          | Default User-Agent header             |
| `verify_ssl`         | bool                     | True                                          | Verify SSL certificates               |
| `ssl_cert_path`      | Optional[str]            | None                                          | Path to custom SSL certificate (.crt) |
| `cookies`            | Optional[Dict[str, str]] | None                                          | Default cookies for all requests      |

### Method Parameters

Both `get()` and `post()` methods accept these optional parameters:

**Return Values:**

- By default, methods return only the `Response` object
- Set `return_cache_info=True` to get a tuple: `(response, cache_hit)` where `cache_hit` is a boolean indicating if the response came from cache

```python
# Default - only response
response = client.get(url)

# With cache info
response, cache_hit = client.get(url, return_cache_info=True)
if cache_hit:
    print("Response from cache!")
```

| Parameter     | Type              | Description                                            |
| ------------- | ----------------- | ------------------------------------------------------ |
| `headers`     | Dict[str, str]    | Custom request headers                                 |
| `retry_count` | int               | Override default retry count                           |
| `proxy`       | Dict[str, str]    | Override default proxy rotation                        |
| `timeout`     | Union[int, float] | Override default timeout                               |
| `verify_ssl`  | Union[bool, str]  | Override SSL verification (True/False or path to .crt) |
| `use_cache`   | bool              | Override cache usage setting                           |
| `cookies`     | Dict[str, str]    | Cookies for request (merges with default)              |

Additional for `post()`:
| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | Union[str, bytes, Dict] | Request body data |
| `json` | Dict[str, Any] | JSON data to send |

## Exception Handling

The library provides specific exceptions for different error conditions:

```python
from request_wrapper import (
    RequestWrapper,
    MaxRetriesExceededError,
    InvalidArgumentError,
    InvalidProxyError,
    SSLError,
    CacheError
)

client = RequestWrapper(retry_count=3)

try:
    response = client.get('https://unreliable-api.example.com')
except MaxRetriesExceededError as e:
    print(f"Failed after {e.max_retries} retries: {e.message}")
    print(f"Last status code: {e.last_status_code}")
except SSLError as e:
    print(f"SSL error for {e.url}: {e.ssl_error}")
except InvalidProxyError as e:
    print(f"Invalid proxy: {e.reason}")
```

## Best Practices

### 1. Resource Management

Always close the client when done:

```python
client = RequestWrapper()
try:
    response = client.get('https://api.example.com/data')
    # Process response...
finally:
    client.close()  # Closes underlying session
```

Or use context manager pattern:

```python
# Note: Context manager support can be added if needed
```

### 2. Error Handling

Handle specific exceptions for better error recovery:

```python
def safe_api_call(url):
    client = RequestWrapper(retry_count=3)

    try:
        return client.get(url)
    except MaxRetriesExceededError:
        # Log and use fallback
        return get_fallback_data()
    except SSLError:
        # Try with SSL verification disabled
        return client.get(url, verify_ssl=False)
```

### 3. Proxy Configuration

Test proxy connectivity before adding to rotation:

```python
def validate_proxy(proxy_dict):
    test_client = RequestWrapper(proxies=[proxy_dict])
    try:
        response = test_client.get('https://httpbin.org/ip', timeout=10)
        return response.status_code == 200
    except Exception:
        return False

# Filter working proxies
working_proxies = [p for p in proxy_list if validate_proxy(p)]
client = RequestWrapper(proxies=working_proxies)
```

### 4. Caching Strategy

Use appropriate cache expiry times:

```python
# For static data - long expiry
static_client = RequestWrapper(
    cache_enabled=True,
    cache_expiry=86400  # 24 hours
)

# For dynamic data - short expiry
dynamic_client = RequestWrapper(
    cache_enabled=True,
    cache_expiry=300    # 5 minutes
)
```

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src/ tests/
isort src/ tests/
```

### Type Checking

```bash
mypy src/
```

### Linting

```bash
flake8 src/ tests/
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

# Dev Testing

```
# Activate environment (run this each time you open a new terminal)
.\venv\Scripts\Activate.ps1

# Run tests
python -m pytest

# Format code
python -m black src/ tests/

# Check code quality
python -m flake8 src/

# Type checking
python -m mypy src/
```

## Changelog

### 0.1.0 (Initial Release)

- Basic GET/POST request support
- Retry logic with configurable status codes
- HTTP caching with Scrapy compatibility
- Proxy rotation support
- Comprehensive error handling
- Full type hint support
