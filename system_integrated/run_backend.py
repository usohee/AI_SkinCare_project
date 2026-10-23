import os

from backend.test import app


if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "5000"))
    debug = os.getenv("APP_ENV", "development").lower() == "development"
    app.run(host=host, port=port, debug=debug)
