from dotenv import load_dotenv
import os

load_dotenv()

EIA_API_KEY = os.getenv("EIA_API_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")


DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

_missing = [k for k, v in {"EIA_API_KEY": EIA_API_KEY}.items() if not v]
if not os.getenv("DATABASE_URL"):
    _missing += [k for k, v in {"DB_HOST": DB_HOST, "DB_NAME": DB_NAME, "DB_USER": DB_USER, "DB_PASSWORD": DB_PASSWORD}.items() if not v]
if _missing:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(_missing)}")
