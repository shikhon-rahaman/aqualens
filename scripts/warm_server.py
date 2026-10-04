"""Server warm-up script: Wake up cold-start servers before a demo.

Pings health endpoint repeatedly until server responds quickly.
Useful for:
- Render free tier (spins down after 15 min idle)
- Hugging Face Spaces (may have cold starts)
- Any serverless/container deployment with cold starts

Usage:
    python scripts/warm_server.py https://your-backend.com
    python scripts/warm_server.py https://aqualens-api.onrender.com

Options:
    --timeout 300       Max seconds to wait (default: 300)
    --target 2.0        Target response time in seconds (default: 2.0)
"""

import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def warm_server(base_url: str, timeout: int = 300, target_time: float = 2.0):
    """Warm up server by repeatedly pinging health endpoint."""
    health_url = f"{base_url.rstrip('/')}/health"
    start_time = time.time()
    attempt = 0

    print(f"Warming up server: {base_url}")
    print(f"Target response time: {target_time}s")
    print(f"Timeout: {timeout}s")
    print("-" * 60)

    while True:
        attempt += 1
        elapsed = time.time() - start_time

        if elapsed > timeout:
            print(f"\n[X] Timeout after {timeout}s")
            print(f"Server may be down or taking too long to start.")
            sys.exit(1)

        try:
            req_start = time.time()
            req = Request(health_url, headers={"User-Agent": "AquaLens-Warmer"})

            with urlopen(req, timeout=30) as response:
                response.read()
                req_time = time.time() - req_start

                status = "[+]" if req_time < target_time else "[~]"
                print(f"Attempt {attempt}: {req_time:.2f}s {status}")

                if req_time < target_time:
                    print("-" * 60)
                    print(f"[+] Server warmed up in {elapsed:.1f}s ({attempt} attempts)")
                    print(f"Response time: {req_time:.2f}s (target: {target_time}s)")
                    sys.exit(0)

        except HTTPError as e:
            print(f"Attempt {attempt}: HTTP {e.code} (waiting...)")
        except URLError as e:
            print(f"Attempt {attempt}: Connection failed (waiting...)")
        except Exception as e:
            print(f"Attempt {attempt}: {type(e).__name__} (waiting...)")

        # Wait before retry, with backoff
        wait_time = min(5, 1 + (attempt * 0.5))
        time.sleep(wait_time)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/warm_server.py <base_url> [--timeout 300] [--target 2.0]")
        print("\nExample:")
        print("  python scripts/warm_server.py https://aqualens-api.onrender.com")
        print("  python scripts/warm_server.py http://localhost:8000 --timeout 60")
        sys.exit(1)

    base_url = sys.argv[1]
    timeout = 300
    target_time = 2.0

    # Parse options
    for i in range(2, len(sys.argv), 2):
        if sys.argv[i] == "--timeout" and i + 1 < len(sys.argv):
            timeout = int(sys.argv[i + 1])
        elif sys.argv[i] == "--target" and i + 1 < len(sys.argv):
            target_time = float(sys.argv[i + 1])

    warm_server(base_url, timeout, target_time)


if __name__ == "__main__":
    main()
