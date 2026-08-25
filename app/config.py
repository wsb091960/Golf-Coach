"""
=========================================================
WSBCO Golf Coach
Configuration

File: app/config.py
Version: 1.0.0
=========================================================
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# -------------------------------------------------------
# PROJECT PATHS
# -------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

APP_DIR = BASE_DIR / "app"

STATIC_DIR = APP_DIR / "static"

TEMPLATE_DIR = APP_DIR / "templates"

UPLOAD_DIR = APP_DIR / "uploads"

DATA_DIR = BASE_DIR / "data"

LOG_DIR = BASE_DIR / "logs"

DATABASE_DIR = DATA_DIR

DATABASE_FILE = DATABASE_DIR / "golfcoach.db"


# -------------------------------------------------------
# CREATE REQUIRED FOLDERS
# -------------------------------------------------------

for directory in [
    DATA_DIR,
    LOG_DIR,
    UPLOAD_DIR,
    UPLOAD_DIR / "videos",
    UPLOAD_DIR / "garmin",
    UPLOAD_DIR / "exports",
    UPLOAD_DIR / "reports",
]:
    directory.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------
# APPLICATION SETTINGS
# -------------------------------------------------------

class Settings(BaseSettings):
    """
    Application configuration.

    Values can be overridden by a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

    # ---------------------------------------------------
    # APPLICATION
    # ---------------------------------------------------

    APP_NAME: str = "WSBCO Golf Coach"

    APP_VERSION: str = "1.0.0"

    ENVIRONMENT: str = "Development"

    DEBUG: bool = True


    # ---------------------------------------------------
    # SERVER
    # ---------------------------------------------------

    HOST: str = "127.0.0.1"

    PORT: int = 8000

    RELOAD: bool = True


    # ---------------------------------------------------
    # DATABASE
    # ---------------------------------------------------

    DATABASE_URL: str = (
        f"sqlite:///{DATABASE_FILE}"
    )


    # ---------------------------------------------------
    # SECURITY
    # ---------------------------------------------------

    SECRET_KEY: str = (
        "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET_KEY"
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


    # ---------------------------------------------------
    # FILE UPLOADS
    # ---------------------------------------------------

    MAX_UPLOAD_SIZE_MB: int = 500

    ALLOWED_VIDEO_EXTENSIONS: list[str] = [
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".m4v",
    ]

    ALLOWED_GARMIN_EXTENSIONS: list[str] = [
        ".csv",
        ".xlsx",
        ".xls",
    ]


    # ---------------------------------------------------
    # COACHING DEFAULTS
    # ---------------------------------------------------

    DEFAULT_UNIT_SYSTEM: str = "Imperial"

    DEFAULT_DISTANCE_UNIT: str = "yards"

    DEFAULT_SPEED_UNIT: str = "mph"

    DEFAULT_HANDICAP_SYSTEM: str = "USGA"


    # ---------------------------------------------------
    # CHART COLORS
    # ---------------------------------------------------

    PRIMARY_COLOR: str = "#0B3D91"

    SECONDARY_COLOR: str = "#1976D2"

    SUCCESS_COLOR: str = "#2E7D32"

    WARNING_COLOR: str = "#F9A825"

    ERROR_COLOR: str = "#C62828"

    BACKGROUND_COLOR: str = "#F5F7FA"

    CARD_COLOR: str = "#FFFFFF"


    # ---------------------------------------------------
    # SESSION SETTINGS
    # ---------------------------------------------------

    DEFAULT_RANGE_BALLS: int = 50

    DEFAULT_TARGET_LINE_COLOR: str = "#00AEEF"

    DEFAULT_DISPERSION_RADIUS: int = 15


    # ---------------------------------------------------
    # REPORT SETTINGS
    # ---------------------------------------------------

    PDF_PAGE_SIZE: str = "LETTER"

    PDF_MARGIN: float = 0.50

    EXPORT_IMAGE_DPI: int = 300


# -------------------------------------------------------
# GLOBAL SETTINGS INSTANCE
# -------------------------------------------------------

settings = Settings()


# -------------------------------------------------------
# VERSION STRING
# -------------------------------------------------------

FULL_VERSION = (
    f"{settings.APP_NAME} "
    f"v{settings.APP_VERSION}"
)


# -------------------------------------------------------
# APPLICATION BANNER
# -------------------------------------------------------

def print_banner() -> None:

    print("=" * 55)

    print(FULL_VERSION)

    print(f"Environment : {settings.ENVIRONMENT}")

    print(f"Database    : {DATABASE_FILE}")

    print("=" * 55)