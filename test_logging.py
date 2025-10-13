#!/usr/bin/env python
"""
Test script to demonstrate RequestWrapper logging functionality.
"""

from request_wrapper import RequestWrapper, configure_logging


def test_default_logging():
    """Test default console logging."""
    print("=== Testing Default Logging (Console) ===")

    client = RequestWrapper(retry_count=2, cache_enabled=True)

    try:
        # This should log to console
        response = client.get('https://httpbin.org/get',
                              params={'test': 'default_logging'})
        print(f"Response Status: {response.status_code}")

        # Test cache functionality with logging
        response2 = client.get('https://httpbin.org/get',
                               params={'test': 'default_logging'})
        print(f"Cached Response Status: {response2.status_code}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()


def test_file_logging():
    """Test file logging configuration."""
    print("\n=== Testing File Logging ===")

    # Configure logging to files
    configure_logging(
        log_level="DEBUG",
        log_file="logs.log",
        error_file="error.log",
        console_output=True  # Keep console output too
    )

    client = RequestWrapper(retry_count=1, cache_enabled=True)

    try:
        # Make a successful request
        response = client.get('https://httpbin.org/get',
                              params={'test': 'file_logging'})
        print(f"Response Status: {response.status_code}")

        # Test retry functionality (this should fail and log errors)
        try:
            response = client.get('https://httpstat.us/500', timeout=3)
        except Exception as e:
            print(f"Expected error occurred: {type(e).__name__}")

        # Test cache operations
        client.clear_cache()

    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        client.close()

    print("Check 'logs.log' and 'error.log' files for detailed logging!")


def test_custom_logging():
    """Test custom logging configuration."""
    print("\n=== Testing Custom Logging Configuration ===")

    # Configure with custom format and error-only file
    configure_logging(
        log_level="WARNING",
        error_file="errors_only.log",
        console_output=True,
        log_format="[%(levelname)s] %(asctime)s - %(message)s"
    )

    client = RequestWrapper(retry_count=1)

    try:
        # This should only log warnings/errors due to log level
        response = client.get('https://httpbin.org/get')
        print(f"Response Status: {response.status_code}")

        # Force an error to test error logging
        try:
            response = client.get('https://httpstat.us/500', timeout=2)
        except Exception as e:
            print(f"Error logged: {type(e).__name__}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    print("🔍 RequestWrapper Logging Test")
    print("=" * 40)

    test_default_logging()
    test_file_logging()
    test_custom_logging()

    print("\n✅ Logging tests completed!")
    print("\nLogging Features:")
    print("- Default: INFO level to stdout")
    print("- Configurable: Level, file output, custom format")
    print("- Files: General logs + Error-only logs")
    print("- Comprehensive: All operations logged (requests, retries, cache, etc.)")
