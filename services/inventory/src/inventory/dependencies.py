from pathlib import Path

from auth import JWTAuth

from inventory.config import settings

auth = JWTAuth(Path(settings.jwt_public_key_path).read_text())
require_admin = auth.require_role("admin")
