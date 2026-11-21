from pathlib import Path
from typing import Annotated

from auth import AccessClaims, JWTAuth
from fastapi import Depends

from inventory.config import settings

auth = JWTAuth(Path(settings.jwt_public_key_path).read_text())
CurrentClaims = Annotated[AccessClaims, Depends(auth)]
AdminClaims = Annotated[AccessClaims, Depends(auth.require_role("admin"))]
