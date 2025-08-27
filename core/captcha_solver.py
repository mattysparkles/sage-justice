import deathbycaptcha
import base64

def solve_captcha(base64_image, username, password):
    client = deathbycaptcha.SocketClient(username, password)
    client.is_verbose = True
    try:
        result = client.decode(base64_image)
        if result:
            return result["text"]
    except Exception as e:
        print(f"Captcha solving failed: {e}")
    return None
