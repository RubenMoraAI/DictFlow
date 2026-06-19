"""Generate dictflow.ico — a modern app icon matching the floating bar.

A dark rounded "squircle" with a subtle gradient and a centered audio
equalizer in a cyan-to-violet gradient. Run: python generate_icon.py
"""
from PIL import Image, ImageDraw

SIZE = 256
RADIUS = 58

# --- Background: vertical gradient inside a rounded square ---
bg_top = (38, 35, 64)      # soft indigo
bg_bottom = (15, 18, 36)   # near-navy
gradient = Image.new("RGBA", (SIZE, SIZE))
gd = ImageDraw.Draw(gradient)
for y in range(SIZE):
    t = y / (SIZE - 1)
    col = tuple(int(bg_top[i] + (bg_bottom[i] - bg_top[i]) * t) for i in range(3)) + (255,)
    gd.line([(0, y), (SIZE, y)], fill=col)

mask = Image.new("L", (SIZE, SIZE), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=RADIUS, fill=255)

icon = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
icon.paste(gradient, (0, 0), mask)

# --- Equalizer bars (cyan -> violet), centered, rounded caps ---
draw = ImageDraw.Draw(icon)
cyan = (56, 189, 248)
violet = (167, 139, 250)
n = 5
bar_w = 22
gap = 14
heights = [0.50, 0.80, 1.00, 0.72, 0.56]
max_h = 168
total = n * bar_w + (n - 1) * gap
x0 = (SIZE - total) // 2
cy = SIZE // 2
for i in range(n):
    t = i / (n - 1)
    color = tuple(int(cyan[k] + (violet[k] - cyan[k]) * t) for k in range(3)) + (255,)
    bx = x0 + i * (bar_w + gap)
    bh = int(heights[i] * max_h)
    draw.rounded_rectangle(
        [bx, cy - bh // 2, bx + bar_w, cy + bh // 2],
        radius=bar_w // 2, fill=color,
    )

icon.save(
    "dictflow.ico",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("dictflow.ico generated.")
