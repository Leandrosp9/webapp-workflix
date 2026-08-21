import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://workflix:workflix@localhost/workflix_test"
)
os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-32-characters")
