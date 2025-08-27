"""Utilities for solving CAPTCHA challenges."""

from typing import Optional

import base64
import binascii
import deathbycaptcha


def solve_captcha(image_data: bytes | str, username: str, password: str) -> Optional[str]:
    """Solve a CAPTCHA image using the DeathByCaptcha service.

    ``image_data`` may be raw bytes or a base64-encoded string.
    """
    client = deathbycaptcha.SocketClient(username, password)
    client.is_verbose = True
    try:
        if isinstance(image_data, str):
            try:
                image_bytes = base64.b64decode(image_data, validate=True)
            except binascii.Error:
                image_bytes = image_data.encode("utf-8")
        else:
            image_bytes = image_data

        result = client.decode(image_bytes)
        if result:
            return result["text"]
    except Exception as e:
        print(f"Captcha solving failed: {e}")
    return None
