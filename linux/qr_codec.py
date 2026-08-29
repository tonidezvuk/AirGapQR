from PIL import Image

import qrcode


def make_qr(
    payload: str,
    box_size: int = 8,
    border: int = 4,
    background_brightness: int = 255
) -> Image.Image:

    background_brightness = max(0, min(255, int(background_brightness)))

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )

    qr.add_data(payload)
    qr.make(fit=True)

    background = (
        background_brightness,
        background_brightness,
        background_brightness
    )

    return qr.make_image(
        fill_color=(0, 0, 0),
        back_color=background
    ).convert("RGB")