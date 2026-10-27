import sys
from pathlib import Path

# Add project root directory to sys.path so modules like app, config, etc. can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app

class VercelPathFixer:
    """
    WSGI Middleware to restore original request paths on Vercel.
    When Vercel uses `rewrites` to route /(.*) -> /api/index,
    Vercel sets PATH_INFO to /api/index while preserving the user's
    actual requested path in HTTP_X_MATCHED_PATH (x-matched-path).
    This middleware restores the original PATH_INFO so Flask's route
    matching handles all URLs (pages, API endpoints, static assets) correctly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched = (
            environ.get("HTTP_X_MATCHED_PATH") or 
            environ.get("HTTP_X_FORWARDED_PATH") or 
            environ.get("HTTP_X_FORWARDED_URI") or 
            environ.get("REQUEST_URI") or 
            ""
        )
        if matched:
            clean_path = matched.split("?")[0].strip()
            if clean_path:
                environ["PATH_INFO"] = clean_path
        elif environ.get("PATH_INFO", "").startswith("/api/index"):
            remainder = environ["PATH_INFO"][len("/api/index"):]
            environ["PATH_INFO"] = remainder if remainder else "/"

        return self.wsgi_app(environ, start_response)

# Apply WSGI middleware
app.wsgi_app = VercelPathFixer(app.wsgi_app)
