"""Generate a 128x128 rainbow gradient BMP test image using only stdlib."""

import struct
import colorsys

WIDTH = 128
HEIGHT = 128
OUTPUT = "output.bmp"


def write_bmp(filename, pixels, width, height):
    """Write a 24-bit BMP file. pixels is list of (R, G, B) tuples, row-major, top-to-bottom."""
    row_size = (width * 3 + 3) & ~3  # rows padded to 4-byte boundary
    pixel_data_size = row_size * height
    file_size = 54 + pixel_data_size

    # BMP Header (14 bytes)
    header = struct.pack('<2sIHHI',
        b'BM',          # signature
        file_size,       # file size
        0,               # reserved
        0,               # reserved
        54               # pixel data offset
    )

    # DIB Header (BITMAPINFOHEADER, 40 bytes)
    dib = struct.pack('<IiiHHIIiiII',
        40,              # header size
        width,           # width
        -height,         # height (negative = top-down)
        1,               # color planes
        24,              # bits per pixel
        0,               # compression (none)
        pixel_data_size, # image size
        2835,            # horizontal resolution (72 DPI)
        2835,            # vertical resolution (72 DPI)
        0,               # colors in palette
        0                # important colors
    )

    with open(filename, 'wb') as f:
        f.write(header)
        f.write(dib)
        for y in range(height):
            row_bytes = bytearray()
            for x in range(width):
                r, g, b = pixels[y * width + x]
                row_bytes += struct.pack('BBB', b, g, r)  # BMP stores BGR
            # Pad row to 4-byte boundary
            while len(row_bytes) % 4 != 0:
                row_bytes += b'\x00'
            f.write(row_bytes)


def generate_rainbow(width, height):
    """Generate rainbow gradient: hue varies with x, brightness varies with y."""
    pixels = []
    for y in range(height):
        for x in range(width):
            hue = x / width
            saturation = 1.0
            value = 1.0 - (y / height) * 0.5  # brightness goes from 1.0 to 0.5
            r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
            pixels.append((int(r * 255), int(g * 255), int(b * 255)))
    return pixels


if __name__ == '__main__':
    pixels = generate_rainbow(WIDTH, HEIGHT)
    write_bmp(OUTPUT, pixels, WIDTH, HEIGHT)
    print(f"Generated {OUTPUT} ({WIDTH}x{HEIGHT})")
