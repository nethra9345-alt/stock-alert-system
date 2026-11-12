import time
import subprocess
import sys
import httpx

def main():
    print("=== Launching FastAPI Uvicorn Server ===")
    server_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    base_url = "http://127.0.0.1:8000"
    endpoints = [
        ("/", "Root Welcome API"),
        ("/docs", "Swagger UI OpenAPI Documentation"),
        ("/api/health", "System & Market Health Check"),
        ("/api/market/overview", "Indian Market Overview & Top Movers"),
        ("/api/market/indices", "Benchmark Indices (NIFTY 50, SENSEX, BANK NIFTY, INDIA VIX)"),
        ("/api/stocks/RELIANCE.NS", "Live Quote (Reliance Industries)"),
        ("/api/stocks/TCS.NS/history?period=1mo&interval=1d", "Historical OHLCV Series (TCS)"),
        ("/api/stocks/HDFCBANK.NS/indicators?period=6mo", "Technical Indicators (HDFC Bank - SMA, EMA, RSI, MACD)"),
        ("/api/watchlist", "Watchlist CRUD"),
        ("/api/portfolio", "Portfolio Analytics & Holdings"),
        ("/api/alerts", "Price Alerts Engine")
    ]

    try:
        # Wait up to 10 seconds for server to start
        print("Waiting for server to become responsive...")
        server_ready = False
        for _ in range(20):
            try:
                res = httpx.get(f"{base_url}/api/health", timeout=1.0)
                if res.status_code == 200:
                    server_ready = True
                    break
            except Exception:
                time.sleep(0.5)

        if not server_ready:
            print("ERROR: Server failed to start in time.")
            stdout, stderr = server_process.communicate(timeout=2)
            print("Server stdout:", stdout)
            print("Server stderr:", stderr)
            sys.exit(1)

        print("Server is UP and HEALTHY! Testing endpoints:\n")
        all_passed = True
        with httpx.Client(base_url=base_url, timeout=10.0) as client:
            for path, desc in endpoints:
                try:
                    response = client.get(path)
                    status = response.status_code
                    if status == 200:
                        print(f" [PASS] ({status}) {desc} -> {path}")
                    else:
                        print(f" [FAIL] ({status}) {desc} -> {path}")
                        all_passed = False
                except Exception as e:
                    print(f" [ERROR] {desc} -> {path}: {e}")
                    all_passed = False

        if all_passed:
            print("\n ALL API ENDPOINTS VERIFIED SUCCESSFULLY!")
        else:
            print("\n SOME ENDPOINTS FAILED.")
            sys.exit(1)

    finally:
        print("\nStopping uvicorn server process...")
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except Exception:
            server_process.kill()
        print("Server cleanly stopped.")

if __name__ == "__main__":
    main()
