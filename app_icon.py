from PIL import Image, ImageDraw


def make_icon_image(size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = size * 0.06
    inner_margin = size * 0.34
    draw.ellipse((margin, margin, size - margin, size - margin), fill=(76, 201, 240, 255))
    draw.ellipse(
        (inner_margin, inner_margin, size - inner_margin, size - inner_margin),
        fill=(26, 26, 46, 255),
    )
    return img


def save_ico(path):
    """Write a multi-resolution .ico for use in Windows shortcuts/taskbar."""
    img = make_icon_image(256)
    img.save(str(path), format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
