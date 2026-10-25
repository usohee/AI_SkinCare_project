"""환경 설정. 비밀값(API 키)은 코드가 아니라 backend/.env 파일에서 읽는다."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
REPO_ROOT = os.path.dirname(BASE_DIR)


def _load_dotenv():
    """python-dotenv가 설치되어 있으면 backend/.env (없으면 레포 루트 .env)를 읽는다.
    이미 터미널에 설정된 환경변수는 덮어쓰지 않는다."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for path in (os.path.join(BASE_DIR, ".env"), os.path.join(REPO_ROOT, ".env")):
        if os.path.exists(path):
            load_dotenv(path, override=False)
            break


_load_dotenv()


class Config:
    DB_PATH = os.environ.get("MIRRORME_DB", os.path.join(BASE_DIR, "skincare.db"))
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
    DEBUG = os.environ.get("DEBUG", "1") == "1"
    MAX_CONTENT_LENGTH = 15 * 1024 * 1024  # 업로드 사진 최대 15MB
    JSON_AS_ASCII = False
