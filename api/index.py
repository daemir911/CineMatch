import sys
import urllib.parse
from pathlib import Path

# Add project root directory to sys.path so modules like app, config, etc. can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app

class VercelPathFixer:
    """
    WSGI Middleware to restore original request paths on Vercel.
    When Vercel uses `rewrites` to route /(.*) -> /api/index?__path=$1,
    the captured path is passed in __path. This middleware extracts __path,
    sets PATH_INFO to the exact user-requested route, and removes __path from
    QUERY_STRING so Flask sees the original, clean request.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        qs = environ.get("QUERY_STRING", "")
        params = urllib.parse.parse_qs(qs, keep_blank_values=True)

        if "__path" in params:
            raw_path = params.pop("__path")[0]
            environ["PATH_INFO"] = "/" + raw_path.lstrip("/")
            # Reconstruct QUERY_STRING without the internal __path parameter
            environ["QUERY_STRING"] = urllib.parse.urlencode(params, doseq=True)
        elif environ.get("HTTP_X_MATCHED_PATH"):
            clean_path = environ["HTTP_X_MATCHED_PATH"].split("?")[0].strip()
            environ["PATH_INFO"] = clean_path or "/"
        elif environ.get("PATH_INFO", "").startswith("/api/index"):
            remainder = environ["PATH_INFO"][len("/api/index"):]
            environ["PATH_INFO"] = remainder if remainder else "/"

        return self.wsgi_app(environ, start_response)

# Apply WSGI middleware
app.wsgi_app = VercelPathFixer(app.wsgi_app)
