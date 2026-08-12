"""Dev authentication via X-User-Id header."""

from __future__ import annotations

import re

from fastapi import Header, HTTPException

_USER_ID_RE = re.compile(r"^[a-zA-Z0-9_\-.:@]{1,128}$")


async def require_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    """Validate the development identity header used until real auth lands."""
    if x_user_id is None or not x_user_id.strip():
        raise HTTPException(
            status_code=401,
            detail="Missing X-User-Id header. Provide a development user id.",
        )
    user_id = x_user_id.strip()
    if not _USER_ID_RE.fullmatch(user_id):
        raise HTTPException(
            status_code=401,
            detail="Invalid X-User-Id header.",
        )
    return user_id
