"""Mirror Me 백엔드 (Flask 애플리케이션 팩토리)."""
import os

from flask import Flask

from .config import Config
from .db import close_db, init_db


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    app.json.ensure_ascii = False  # 응답 JSON에서 한글이 \uXXXX로 깨지지 않게 한다

    init_db(app.config["DB_PATH"])
    app.teardown_appcontext(close_db)

    from .routes import register_blueprints
    register_blueprints(app)

    # 다른 컴퓨터에서 연 시연 HTML(file://)이 이 서버를 호출할 수 있도록 허용한다.
    @app.after_request
    def _cors(resp):
        resp.headers.setdefault("Access-Control-Allow-Origin", "*")
        resp.headers.setdefault("Access-Control-Allow-Headers", "Content-Type")
        resp.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        return resp

    from .routes.demo import ensure_demo_user
    ensure_demo_user(app.config["DB_PATH"])
    return app
