"""Entry point for running the API server."""
from app.main import app

if __name__ == "__main__":
    import uvicorn
    from app.config import get_settings
    s = get_settings()
    uvicorn.run("app.main:app", host=s.app_host, port=s.app_port, reload=(s.app_env == "development"))
