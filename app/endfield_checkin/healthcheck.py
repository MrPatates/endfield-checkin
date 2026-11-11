"""Docker HEALTHCHECK: exit 0 when the web server answers /healthz."""

import os
import sys
import urllib.request

try:
    port = int(os.environ.get("WEBUI_PORT", "8080"))
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=5) as response:
        sys.exit(0 if response.status == 200 else 1)
except Exception:
    sys.exit(1)
