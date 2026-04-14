import logging
import subprocess
import sys
import threading
import time

import requests
import uvicorn

from api import api_app
from config import API_HOST, API_PORT, STREAMLIT_PORT

logger = logging.getLogger(__name__)


def run_api() -> None:
    uvicorn.run(api_app, host=API_HOST, port=API_PORT, log_level="info")


def wait_for_api(timeout_seconds: int = 10) -> bool:
    deadline = time.time() + timeout_seconds
    api_url = f"http://127.0.0.1:{API_PORT}/"

    while time.time() < deadline:
        try:
            response = requests.get(api_url, timeout=2)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


def launch_streamlit() -> int:
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "Home.py",
        "--server.port",
        str(STREAMLIT_PORT),
    ]
    logger.info("Launching Streamlit on port %s", STREAMLIT_PORT)
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def main() -> int:
    logger.info("Starting API server on %s:%s", API_HOST, API_PORT)
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    if not wait_for_api():
        logger.error("API did not become ready in time")
        return 1

    logger.info("API is ready")
    return launch_streamlit()


if __name__ == "__main__":
    raise SystemExit(main())
