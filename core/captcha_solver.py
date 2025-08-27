"""Utilities for solving CAPTCHA challenges."""

from typing import Optional

import base64
import deathbycaptcha


def solve_captcha(base64_image: str, username: str, password: str) -> Optional[str]:
    """Solve a CAPTCHA image using the DeathByCaptcha service.

    Args:
        base64_image: CAPTCHA image encoded as a base64 string.
        username: DeathByCaptcha account username.
        password: DeathByCaptcha account password.

    Returns:
        The solved CAPTCHA text if successful, otherwise ``None``.
    """
    client = deathbycaptcha.SocketClient(username, password)
    client.is_verbose = True
    try:
        image_bytes = base64.b64decode(base64_image)
        result = client.decode(image_bytes)
        if result:
            return result["text"]
    except Exception as e:
        print(f"Captcha solving failed: {e}")
    return None
