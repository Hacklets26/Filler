import os

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
JWT_SECRET = os.getenv("JWT_SECRET", "patchwork-development-secret-change-before-deploy")
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "https://backend.ifamished.com").rstrip("/")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://patchwork.hacklets.dev").rstrip("/")
MAX_VIDEO_BYTES = 50 * 1024 * 1024
