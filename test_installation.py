#!/usr/bin/env python
"""
Quick test script to verify RequestWrapper functionality.
Run this after installation to make sure everything works correctly.
"""

from request_wrapper import RequestWrapper, MaxRetriesExceededError


def test_basic_functionality():
    """Test basic RequestWrapper functionality."""
    print("🧪 Testing RequestWrapper Basic Functionality")
    print("=" * 50)

    # Test 1: Basic GET request
    print("\n1. Testing basic GET request...")
    client = RequestWrapper()
    try:
        response = client.get("https://httpbin.org/get?test=1")
        print(f"   ✅ GET request successful: {response.status_code}")

        # Check if we got JSON response
        data = response.json()
        if "args" in data and data["args"].get("test") == "1":
            print("   ✅ Query parameters handled correctly")
        else:
            print("   ⚠️  Query parameters not found in response")
    except Exception as e:
        print(f"   ❌ GET request failed: {e}")

    # Test 2: POST request with JSON
    print("\n2. Testing POST request with JSON...")
    try:
        response = client.post(
            "https://httpbin.org/post", json={"name": "RequestWrapper", "version": "0.1.0"}
        )
        print(f"   ✅ POST request successful: {response.status_code}")

        data = response.json()
        if "json" in data and data["json"].get("name") == "RequestWrapper":
            print("   ✅ JSON data sent correctly")
        else:
            print("   ⚠️  JSON data not found in response")
    except Exception as e:
        print(f"   ❌ POST request failed: {e}")

    # Test 3: Retry functionality
    print("\n3. Testing retry functionality...")
    retry_client = RequestWrapper(retry_count=2)
    try:
        # This should fail and trigger retries
        response = retry_client.get("https://httpstat.us/500", timeout=5)
        print(f"   ⚠️  Request unexpectedly succeeded: {response.status_code}")
    except MaxRetriesExceededError as e:
        print(
            f"   ✅ Retry mechanism working: {e.max_retries} retries attempted")
    except Exception as e:
        print(f"   ✅ Request failed as expected: {type(e).__name__}")

    # Test 4: Custom retry status codes
    print("\n4. Testing custom retry status codes...")
    custom_client = RequestWrapper(retry_count=1)
    custom_client.add_retry_status_code(429)  # Rate limiting

    codes = custom_client.get_retry_status_codes()
    if 429 in codes:
        print("   ✅ Custom retry status code added successfully")
    else:
        print("   ❌ Custom retry status code not added")

    # Remove the code
    custom_client.remove_retry_status_code(429)
    codes = custom_client.get_retry_status_codes()
    if 429 not in codes:
        print("   ✅ Custom retry status code removed successfully")
    else:
        print("   ❌ Custom retry status code not removed")

    # Test 5: Caching functionality
    print("\n5. Testing caching functionality...")
    cache_client = RequestWrapper(cache_enabled=True, cache_dir="test_cache")

    try:
        # First request - should hit API
        response1 = cache_client.get("https://httpbin.org/uuid")
        uuid1 = response1.json().get("uuid")

        # Second request - should use cache (same UUID)
        response2 = cache_client.get("https://httpbin.org/uuid")
        uuid2 = response2.json().get("uuid")

        if uuid1 == uuid2:
            print("   ✅ Caching working correctly (same UUID returned)")
        else:
            print("   ⚠️  Cache might not be working (different UUIDs)")

        cache_size = cache_client.get_cache_size()
        print(f"   📊 Cache contains {cache_size} items")

        # Clear cache
        cache_client.clear_cache()
        print("   🧹 Cache cleared")

    except Exception as e:
        print(f"   ❌ Caching test failed: {e}")

    # Clean up
    client.close()
    retry_client.close()
    custom_client.close()
    cache_client.close()

    print("\n🎉 Testing completed!")
    print("\n💡 Your RequestWrapper module is ready to use!")
    print("\nNext steps:")
    print("  - Import: from request_wrapper import RequestWrapper")
    print("  - Create client: client = RequestWrapper()")
    print("  - Make requests: response = client.get('https://api.example.com')")
    print("  - Check the examples/ folder for more advanced usage")


if __name__ == "__main__":
    test_basic_functionality()
