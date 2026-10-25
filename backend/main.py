"""서버 실행:  python main.py   →  http://127.0.0.1:5000"""
from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
