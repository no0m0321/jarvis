from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

root = Path(__file__).resolve().parents[1]
out_dir = root / "assets"
out_dir.mkdir(parents=True, exist_ok=True)
size = 1024
img = Image.new("RGBA", (size, size), (2, 8, 20, 255))

# radial background
center = (size / 2, size / 2)
pix = img.load()
for y in range(size):
    for x in range(size):
        dx = (x - center[0]) / size
        dy = (y - center[1]) / size
        d = min(1.0, (dx * dx + dy * dy) ** 0.5 * 2.2)
        r = int(5 + (6 * (1 - d)))
        g = int(15 + (55 * (1 - d)))
        b = int(36 + (95 * (1 - d)))
        pix[x, y] = (r, g, b, 255)

# glow layers
draw = ImageDraw.Draw(img, "RGBA")
for radius, alpha in [(390, 38), (300, 55), (220, 82), (140, 135)]:
    box = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
    draw.ellipse(box, outline=(76, 232, 255, alpha), width=max(6, radius // 22))

# core orb
orb = Image.new("RGBA", (size, size), (0, 0, 0, 0))
od = ImageDraw.Draw(orb, "RGBA")
for r, color in [
    (250, (65, 215, 255, 38)),
    (190, (104, 109, 255, 70)),
    (140, (66, 230, 255, 145)),
    (96, (176, 246, 255, 220)),
]:
    od.ellipse([center[0]-r, center[1]-r, center[0]+r, center[1]+r], fill=color)
orb = orb.filter(ImageFilter.GaussianBlur(8))
img = Image.alpha_composite(img, orb)
draw = ImageDraw.Draw(img, "RGBA")

# angular frame
pad = 145
for i, color in enumerate([(68, 227, 255, 210), (147, 91, 255, 170), (255, 255, 255, 75)]):
    off = i * 24
    draw.rounded_rectangle([pad+off, pad+off, size-pad-off, size-pad-off], radius=130, outline=color, width=12-i*3)

# J monogram
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 420)
except Exception:
    font = ImageFont.load_default()
text = "J"
bbox = draw.textbbox((0, 0), text, font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
pos = ((size - tw) / 2 - 5, (size - th) / 2 - 60)
for offset, color in [((0, 0), (255, 255, 255, 245)), ((16, 18), (58, 222, 255, 70)), ((-14, -12), (150, 90, 255, 55))]:
    draw.text((pos[0]+offset[0], pos[1]+offset[1]), text, font=font, fill=color)

# small command dots
for angle in range(0, 360, 45):
    import math
    rad = math.radians(angle)
    x = center[0] + math.cos(rad) * 345
    y = center[1] + math.sin(rad) * 345
    draw.ellipse([x-12, y-12, x+12, y+12], fill=(102, 231, 255, 180))

for target in ["icon.png", "icon@2x.png"]:
    img.save(out_dir / target)

# also generate common Linux icon sizes
for s in [16, 32, 64, 128, 256, 512]:
    resized = img.resize((s, s), Image.LANCZOS)
    resized.save(out_dir / f"{s}x{s}.png")
print(out_dir / "icon.png")
