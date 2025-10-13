# RequestWrapper Example Usage

from request_wrapper import RequestWrapper, MaxRetriesExceededError, SSLError


def main():
    """Demonstrate RequestWrapper usage with examples."""

    print("=== RequestWrapper Demo ===\n")

    # Example 1: Basic usage
    print("1. Basic GET request:")
    client = RequestWrapper()

    try:
        response = client.get("https://httpbin.org/get")
        print(f"   Status: {response.status_code}")
        print(f"   Response length: {len(response.content)} bytes")
    except Exception as e:
        print(f"   Error: {e}")

    print()

    # Example 2: POST request with JSON
    print("2. POST request with JSON:")
    try:
        response = client.post(
            "https://httpbin.org/post", json={"name": "John Doe", "age": 30}
        )
        print(f"   Status: {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")

    print()

    # Example 3: Retry configuration
    print("3. Client with custom retry settings:")
    retry_client = RequestWrapper(
        retry_count=2, retry_status_codes=[500, 502, 503])

    # Add rate limiting to retry list
    retry_client.add_retry_status_code(429)
    print(f"   Retry status codes: {retry_client.get_retry_status_codes()}")

    print()

    # Example 4: Caching demonstration
    print("4. Caching demonstration:")
    cache_client = RequestWrapper(
        cache_enabled=True, cache_dir="demo_cache", cache_expiry=60  # 1 minute expiry
    )

    try:
        # First request (hits API)
        print("   Making first request (will hit API)...")
        response1 = cache_client.get("https://httpbin.org/uuid")

        # Second request (from cache)
        print("   Making second request (should use cache)...")
        response2 = cache_client.get("https://httpbin.org/uuid")

        print(f"   Cache size: {cache_client.get_cache_size()} items")

        # Clear cache
        cache_client.clear_cache()
        print("   Cache cleared")

    except Exception as e:
        print(f"   Error: {e}")

    print()

    # Example 5: Error handling
    print("5. Error handling demonstration:")
    error_client = RequestWrapper(retry_count=1)

    try:
        # This will likely fail and demonstrate retry logic
        response = error_client.get("https://httpstat.us/500", timeout=5)
    except MaxRetriesExceededError as e:
        print(f"   Max retries exceeded: {e.message}")
        print(f"   URL: {e.url}")
        print(f"   Max retries: {e.max_retries}")
        print(f"   Last status: {e.last_status_code}")
    except Exception as e:
        print(f"   Other error: {e}")

    print()

    # Example 6: Proxy configuration (commented out since we don't have test proxies)
    print("6. Proxy configuration example (not executed):")
    print(
        """
    proxies = [
        {'http': 'http://proxy1:8080', 'https': 'http://proxy1:8080'},
        {'http': 'http://proxy2:8080', 'https': 'http://proxy2:8080'}
    ]

    proxy_client = RequestWrapper(
        proxies=proxies,
        retry_count=3
    )

    # Requests will rotate through proxies
    response = proxy_client.get('https://httpbin.org/ip')
    """
    )

    # Clean up
    client.close()
    retry_client.close()
    cache_client.close()
    error_client.close()

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
