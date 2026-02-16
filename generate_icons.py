"""Generate PWA app icons as simple PNGs using only the standard library."""
import struct
import zlib
import os

def create_png(width, height, pixels):
    """Create a minimal PNG file from raw pixel data."""
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))

    raw = b""
    for y in range(height):
        raw += b"\x00"  # filter byte
        for x in range(width):
            raw += pixels[y][x]

    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return header + ihdr + idat + iend


def draw_icon(size):
    """Draw a stock chart icon with trend line."""
    bg = (15, 23, 42)       # dark navy
    accent = (59, 130, 246) # blue
    green = (34, 197, 94)   # green
    white = (241, 245, 249) # off-white

    pixels = [[bytes(bg) for _ in range(size)] for _ in range(size)]

    def set_pixel(x, y, color):
        if 0 <= x < size and 0 <= y < size:
            pixels[y][x] = bytes(color)

    def fill_rect(x1, y1, x2, y2, color):
        for y in range(max(0, y1), min(size, y2)):
            for x in range(max(0, x1), min(size, x2)):
                set_pixel(x, y, color)

    def draw_thick_line(x1, y1, x2, y2, color, thickness=2):
        steps = max(abs(x2 - x1), abs(y2 - y1), 1) * 2
        for i in range(steps + 1):
            t = i / steps
            x = int(x1 + (x2 - x1) * t)
            y = int(y1 + (y2 - y1) * t)
            for dy in range(-thickness, thickness + 1):
                for dx in range(-thickness, thickness + 1):
                    if dx * dx + dy * dy <= thickness * thickness:
                        set_pixel(x + dx, y + dy, color)

    # Rounded corner background
    margin = size // 8
    fill_rect(0, 0, size, size, bg)

    # Draw a stylized uptrend chart
    pad = size // 5
    chart_h = size - 2 * pad

    # Bar chart bars (subtle)
    bar_color = (30, 41, 59)  # slightly lighter bg
    num_bars = 5
    bar_w = (size - 2 * pad) // (num_bars * 2)
    bar_heights = [0.3, 0.5, 0.4, 0.7, 0.9]
    for i, h in enumerate(bar_heights):
        bx = pad + i * (size - 2 * pad) // num_bars + bar_w // 2
        by = int(size - pad - chart_h * h)
        fill_rect(bx, by, bx + bar_w, size - pad, bar_color)

    # Draw uptrend line (green)
    points = [
        (pad, size - pad - int(chart_h * 0.3)),
        (pad + (size - 2 * pad) // 4, size - pad - int(chart_h * 0.45)),
        (pad + (size - 2 * pad) // 2, size - pad - int(chart_h * 0.35)),
        (pad + 3 * (size - 2 * pad) // 4, size - pad - int(chart_h * 0.65)),
        (size - pad, size - pad - int(chart_h * 0.85)),
    ]
    thickness = max(size // 64, 2)
    for i in range(len(points) - 1):
        draw_thick_line(points[i][0], points[i][1],
                       points[i+1][0], points[i+1][1], green, thickness)

    # Draw dot at end
    ex, ey = points[-1]
    dot_r = max(size // 40, 3)
    for dy in range(-dot_r, dot_r + 1):
        for dx in range(-dot_r, dot_r + 1):
            if dx*dx + dy*dy <= dot_r*dot_r:
                set_pixel(ex + dx, ey + dy, white)

    # "S" letter in top-left
    s_size = size // 6
    s_x = pad + 2
    s_y = pad + 2
    letter_t = max(size // 80, 2)
    # Top curve of S
    draw_thick_line(s_x + s_size, s_y, s_x, s_y, accent, letter_t)
    draw_thick_line(s_x, s_y, s_x, s_y + s_size // 2, accent, letter_t)
    draw_thick_line(s_x, s_y + s_size // 2, s_x + s_size, s_y + s_size // 2, accent, letter_t)
    draw_thick_line(s_x + s_size, s_y + s_size // 2, s_x + s_size, s_y + s_size, accent, letter_t)
    draw_thick_line(s_x + s_size, s_y + s_size, s_x, s_y + s_size, accent, letter_t)

    return create_png(size, size, pixels)


os.makedirs("static/icons", exist_ok=True)
for sz in [192, 512]:
    data = draw_icon(sz)
    path = f"static/icons/icon-{sz}.png"
    with open(path, "wb") as f:
        f.write(data)
    print(f"Generated {path} ({len(data)} bytes)")
