"""
Pure-Python JPEG Encoder/Decoder — No external libraries.

Implements baseline JPEG (JFIF) encoding and decoding using only Python stdlib.
Supports quality settings 0-100 and produces files compatible with standard
JPEG decoders (browsers, ImageMagick, etc).

Usage:
    python jpeg_codec.py encode input.bmp output.jpg [--quality 75]
    python jpeg_codec.py decode input.jpg output.bmp
"""

import math
import struct
import argparse
from collections import defaultdict

# ============================================================================
# JPEG Standard Tables
# ============================================================================

# Standard luminance quantization table (Table K.1 from JPEG spec)
STD_LUMINANCE_QUANT = [
    16, 11, 10, 16, 24, 40, 51, 61,
    12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56,
    14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77,
    24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101,
    72, 92, 95, 98, 112, 100, 103, 99,
]

# Standard chrominance quantization table (Table K.2 from JPEG spec)
STD_CHROMINANCE_QUANT = [
    17, 18, 24, 47, 99, 99, 99, 99,
    18, 21, 26, 66, 99, 99, 99, 99,
    24, 26, 56, 99, 99, 99, 99, 99,
    47, 66, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
]

# Zigzag order for 8x8 block
ZIGZAG_ORDER = [
    0,  1,  8,  16, 9,  2,  3,  10,
    17, 24, 32, 25, 18, 11, 4,  5,
    12, 19, 26, 33, 40, 48, 41, 34,
    27, 20, 13, 6,  7,  14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36,
    29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46,
    53, 60, 61, 54, 47, 55, 62, 63,
]

# Inverse zigzag: position -> zigzag index
ZIGZAG_INV = [0] * 64
for i, z in enumerate(ZIGZAG_ORDER):
    ZIGZAG_INV[z] = i

# Standard Huffman tables from JPEG spec (Annex K)
# DC Luminance (Table K.3)
DC_LUMINANCE_BITS = [0, 0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
DC_LUMINANCE_VALS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

# DC Chrominance (Table K.4)
DC_CHROMINANCE_BITS = [0, 0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
DC_CHROMINANCE_VALS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

# AC Luminance (Table K.5)
AC_LUMINANCE_BITS = [0, 0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 0x7d]
AC_LUMINANCE_VALS = [
    0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12,
    0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
    0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xa1, 0x08,
    0x23, 0x42, 0xb1, 0xc1, 0x15, 0x52, 0xd1, 0xf0,
    0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0a, 0x16,
    0x17, 0x18, 0x19, 0x1a, 0x25, 0x26, 0x27, 0x28,
    0x29, 0x2a, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39,
    0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
    0x4a, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
    0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
    0x6a, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79,
    0x7a, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
    0x8a, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98,
    0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7,
    0xa8, 0xa9, 0xaa, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6,
    0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3, 0xc4, 0xc5,
    0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xd2, 0xd3, 0xd4,
    0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda, 0xe1, 0xe2,
    0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9, 0xea,
    0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8,
    0xf9, 0xfa,
]

# AC Chrominance (Table K.6)
AC_CHROMINANCE_BITS = [0, 0, 2, 1, 2, 4, 4, 3, 4, 7, 5, 4, 4, 0, 1, 2, 0x77]
AC_CHROMINANCE_VALS = [
    0x00, 0x01, 0x02, 0x03, 0x11, 0x04, 0x05, 0x21,
    0x31, 0x06, 0x12, 0x41, 0x51, 0x07, 0x61, 0x71,
    0x13, 0x22, 0x32, 0x81, 0x08, 0x14, 0x42, 0x91,
    0xa1, 0xb1, 0xc1, 0x09, 0x23, 0x33, 0x52, 0xf0,
    0x15, 0x62, 0x72, 0xd1, 0x0a, 0x16, 0x24, 0x34,
    0xe1, 0x25, 0xf1, 0x17, 0x18, 0x19, 0x1a, 0x26,
    0x27, 0x28, 0x29, 0x2a, 0x35, 0x36, 0x37, 0x38,
    0x39, 0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
    0x49, 0x4a, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58,
    0x59, 0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68,
    0x69, 0x6a, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78,
    0x79, 0x7a, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
    0x88, 0x89, 0x8a, 0x92, 0x93, 0x94, 0x95, 0x96,
    0x97, 0x98, 0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5,
    0xa6, 0xa7, 0xa8, 0xa9, 0xaa, 0xb2, 0xb3, 0xb4,
    0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3,
    0xc4, 0xc5, 0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xd2,
    0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda,
    0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9,
    0xea, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8,
    0xf9, 0xfa,
]


# ============================================================================
# Huffman Table Utilities
# ============================================================================

def build_huffman_encode_table(bits, vals):
    """Build encoding table: value -> (code, length) from JPEG-style bits/vals."""
    table = {}
    code = 0
    vi = 0
    for length in range(1, 17):
        count = bits[length]
        for _ in range(count):
            table[vals[vi]] = (code, length)
            code += 1
            vi += 1
        code <<= 1
    return table


def build_huffman_decode_table(bits, vals):
    """Build decoding table for Huffman. Returns list of (code, length, value)."""
    entries = []
    code = 0
    vi = 0
    for length in range(1, 17):
        count = bits[length]
        for _ in range(count):
            entries.append((code, length, vals[vi]))
            code += 1
            vi += 1
        code <<= 1
    return entries


# ============================================================================
# DCT / IDCT
# ============================================================================

# Precompute cosine table for DCT
_COS_TABLE = [[0.0] * 8 for _ in range(8)]
for _u in range(8):
    for _x in range(8):
        _COS_TABLE[_u][_x] = math.cos((2 * _x + 1) * _u * math.pi / 16)


def dct_2d(block):
    """Forward 2D DCT on an 8x8 block. Input/output are flat 64-element lists."""
    # Separate row and column transforms for efficiency
    temp = [0.0] * 64

    # Row transform
    for row in range(8):
        for u in range(8):
            s = 0.0
            for x in range(8):
                s += block[row * 8 + x] * _COS_TABLE[u][x]
            cu = 1.0 / math.sqrt(2) if u == 0 else 1.0
            temp[row * 8 + u] = 0.5 * cu * s

    # Column transform
    result = [0.0] * 64
    for col in range(8):
        for v in range(8):
            s = 0.0
            for y in range(8):
                s += temp[y * 8 + col] * _COS_TABLE[v][y]
            cv = 1.0 / math.sqrt(2) if v == 0 else 1.0
            result[v * 8 + col] = 0.5 * cv * s

    return result


def idct_2d(block):
    """Inverse 2D DCT on an 8x8 block. Input/output are flat 64-element lists."""
    temp = [0.0] * 64

    # Column transform first
    for col in range(8):
        for y in range(8):
            s = 0.0
            for v in range(8):
                cv = 1.0 / math.sqrt(2) if v == 0 else 1.0
                s += cv * block[v * 8 + col] * _COS_TABLE[v][y]
            temp[y * 8 + col] = 0.5 * s

    # Row transform
    result = [0.0] * 64
    for row in range(8):
        for x in range(8):
            s = 0.0
            for u in range(8):
                cu = 1.0 / math.sqrt(2) if u == 0 else 1.0
                s += cu * temp[row * 8 + u] * _COS_TABLE[u][x]
            result[row * 8 + x] = 0.5 * s

    return result


# ============================================================================
# Quantization
# ============================================================================

def scale_quant_table(base_table, quality):
    """Scale a quantization table based on quality (1-100). Same formula as libjpeg."""
    if quality <= 0:
        quality = 1
    if quality > 100:
        quality = 100
    if quality < 50:
        scale = 5000 // quality
    else:
        scale = 200 - quality * 2
    table = []
    for v in base_table:
        q = (v * scale + 50) // 100
        q = max(1, min(255, q))
        table.append(q)
    return table


def quantize(dct_block, quant_table):
    """Quantize DCT coefficients."""
    return [int(round(dct_block[i] / quant_table[i])) for i in range(64)]


def dequantize(quant_block, quant_table):
    """Dequantize coefficients."""
    return [quant_block[i] * quant_table[i] for i in range(64)]


# ============================================================================
# Zigzag
# ============================================================================

def zigzag_scan(block):
    """Reorder a flat 64-element block into zigzag order."""
    return [block[ZIGZAG_ORDER[i]] for i in range(64)]


def zigzag_unscan(zigzag_block):
    """Reverse zigzag ordering back to natural 8x8 order."""
    block = [0] * 64
    for i in range(64):
        block[ZIGZAG_ORDER[i]] = zigzag_block[i]
    return block


# ============================================================================
# Color Space Conversion
# ============================================================================

def rgb_to_ycbcr(r, g, b):
    """Convert RGB to YCbCr (JFIF standard)."""
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = -0.1687 * r - 0.3313 * g + 0.5 * b + 128
    cr = 0.5 * r - 0.4187 * g - 0.0813 * b + 128
    return y, cb, cr


def ycbcr_to_rgb(y, cb, cr):
    """Convert YCbCr back to RGB."""
    r = y + 1.402 * (cr - 128)
    g = y - 0.34414 * (cb - 128) - 0.71414 * (cr - 128)
    b = y + 1.772 * (cb - 128)
    return (
        max(0, min(255, int(round(r)))),
        max(0, min(255, int(round(g)))),
        max(0, min(255, int(round(b)))),
    )


# ============================================================================
# BMP I/O
# ============================================================================

def read_bmp(filename):
    """Read a 24-bit BMP file. Returns (width, height, pixels) where pixels is
    list of (R, G, B) tuples, row-major, top-to-bottom."""
    with open(filename, 'rb') as f:
        # BMP header
        sig = f.read(2)
        if sig != b'BM':
            raise ValueError("Not a BMP file")
        file_size = struct.unpack('<I', f.read(4))[0]
        f.read(4)  # reserved
        pixel_offset = struct.unpack('<I', f.read(4))[0]

        # DIB header
        header_size = struct.unpack('<I', f.read(4))[0]
        width = struct.unpack('<i', f.read(4))[0]
        height = struct.unpack('<i', f.read(4))[0]
        planes = struct.unpack('<H', f.read(2))[0]
        bpp = struct.unpack('<H', f.read(2))[0]

        if bpp != 24:
            raise ValueError(f"Only 24-bit BMP supported, got {bpp}-bit")

        # Skip rest of DIB header
        f.seek(pixel_offset)

        top_down = height < 0
        abs_height = abs(height)
        row_size = (width * 3 + 3) & ~3

        rows = []
        for _ in range(abs_height):
            row_data = f.read(row_size)
            row = []
            for x in range(width):
                b_val = row_data[x * 3]
                g_val = row_data[x * 3 + 1]
                r_val = row_data[x * 3 + 2]
                row.append((r_val, g_val, b_val))
            rows.append(row)

        if not top_down:
            rows.reverse()

        pixels = []
        for row in rows:
            pixels.extend(row)

        return width, abs_height, pixels


def write_bmp(filename, width, height, pixels):
    """Write a 24-bit BMP file. pixels is list of (R, G, B) tuples."""
    row_size = (width * 3 + 3) & ~3
    pixel_data_size = row_size * height
    file_size = 54 + pixel_data_size

    with open(filename, 'wb') as f:
        # BMP Header
        f.write(struct.pack('<2sIHHI', b'BM', file_size, 0, 0, 54))
        # DIB Header (BITMAPINFOHEADER)
        f.write(struct.pack('<IiiHHIIiiII',
            40, width, -height, 1, 24, 0, pixel_data_size, 2835, 2835, 0, 0))

        for y in range(height):
            row_bytes = bytearray()
            for x in range(width):
                r, g, b = pixels[y * width + x]
                row_bytes += struct.pack('BBB', b, g, r)
            while len(row_bytes) % 4 != 0:
                row_bytes += b'\x00'
            f.write(row_bytes)


# ============================================================================
# TIFF I/O (uncompressed only)
# ============================================================================

# TIFF tag IDs
_TIFF_IMAGE_WIDTH = 256
_TIFF_IMAGE_LENGTH = 257
_TIFF_BITS_PER_SAMPLE = 258
_TIFF_COMPRESSION = 259
_TIFF_PHOTOMETRIC = 262
_TIFF_STRIP_OFFSETS = 273
_TIFF_SAMPLES_PER_PIXEL = 277
_TIFF_ROWS_PER_STRIP = 278
_TIFF_STRIP_BYTE_COUNTS = 279
_TIFF_X_RESOLUTION = 282
_TIFF_Y_RESOLUTION = 283
_TIFF_RESOLUTION_UNIT = 296


def read_tiff(filename):
    """Read an uncompressed 24-bit RGB TIFF file.
    Returns (width, height, pixels) where pixels is list of (R, G, B) tuples."""
    with open(filename, 'rb') as f:
        data = f.read()

    # Header: byte order + magic + IFD offset
    byte_order = data[0:2]
    if byte_order == b'II':
        endian = '<'
    elif byte_order == b'MM':
        endian = '>'
    else:
        raise ValueError("Not a TIFF file (bad byte order)")

    magic = struct.unpack_from(endian + 'H', data, 2)[0]
    if magic != 42:
        raise ValueError(f"Not a TIFF file (magic={magic}, expected 42)")

    ifd_offset = struct.unpack_from(endian + 'I', data, 4)[0]

    # Parse IFD entries
    num_entries = struct.unpack_from(endian + 'H', data, ifd_offset)[0]
    tags = {}
    pos = ifd_offset + 2

    for _ in range(num_entries):
        tag_id = struct.unpack_from(endian + 'H', data, pos)[0]
        type_id = struct.unpack_from(endian + 'H', data, pos + 2)[0]
        count = struct.unpack_from(endian + 'I', data, pos + 4)[0]
        value_offset_raw = data[pos + 8:pos + 12]

        # Type sizes: 1=BYTE(1), 2=ASCII(1), 3=SHORT(2), 4=LONG(4), 5=RATIONAL(8)
        type_sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8}
        type_fmts = {1: 'B', 3: 'H', 4: 'I'}
        tsize = type_sizes.get(type_id, 1)

        if count * tsize <= 4:
            # Value fits in offset field
            if type_id in type_fmts:
                values = []
                for i in range(count):
                    v = struct.unpack_from(endian + type_fmts[type_id], value_offset_raw, i * tsize)[0]
                    values.append(v)
            else:
                values = [struct.unpack_from(endian + 'I', value_offset_raw, 0)[0]]
        else:
            # Value is at offset
            val_off = struct.unpack_from(endian + 'I', value_offset_raw, 0)[0]
            if type_id in type_fmts:
                values = []
                for i in range(count):
                    v = struct.unpack_from(endian + type_fmts[type_id], data, val_off + i * tsize)[0]
                    values.append(v)
            elif type_id == 5:  # RATIONAL
                values = []
                for i in range(count):
                    num = struct.unpack_from(endian + 'I', data, val_off + i * 8)[0]
                    den = struct.unpack_from(endian + 'I', data, val_off + i * 8 + 4)[0]
                    values.append((num, den))
            else:
                values = [val_off]

        tags[tag_id] = values[0] if count == 1 else values
        pos += 12

    width = tags.get(_TIFF_IMAGE_WIDTH, 0)
    height = tags.get(_TIFF_IMAGE_LENGTH, 0)
    compression = tags.get(_TIFF_COMPRESSION, 1)
    photometric = tags.get(_TIFF_PHOTOMETRIC, 2)
    samples = tags.get(_TIFF_SAMPLES_PER_PIXEL, 3)
    bps = tags.get(_TIFF_BITS_PER_SAMPLE, 8)
    if isinstance(bps, list):
        bps = bps[0]
    rows_per_strip = tags.get(_TIFF_ROWS_PER_STRIP, height)

    if compression != 1:
        raise ValueError(f"Only uncompressed TIFF supported (compression={compression})")
    if bps != 8:
        raise ValueError(f"Only 8-bit TIFF supported (bits_per_sample={bps})")

    strip_offsets = tags.get(_TIFF_STRIP_OFFSETS, 0)
    if not isinstance(strip_offsets, list):
        strip_offsets = [strip_offsets]

    strip_byte_counts = tags.get(_TIFF_STRIP_BYTE_COUNTS, width * height * samples)
    if not isinstance(strip_byte_counts, list):
        strip_byte_counts = [strip_byte_counts]

    # Read pixel data from strips
    pixels = []
    row = 0
    for si, (soff, scount) in enumerate(zip(strip_offsets, strip_byte_counts)):
        strip_data = data[soff:soff + scount]
        strip_rows = min(rows_per_strip, height - row)
        for r in range(strip_rows):
            for x in range(width):
                base = r * width * samples + x * samples
                if samples >= 3:
                    rv = strip_data[base]
                    gv = strip_data[base + 1]
                    bv = strip_data[base + 2]
                else:
                    rv = gv = bv = strip_data[base]

                if photometric == 0:  # MinIsWhite
                    rv, gv, bv = 255 - rv, 255 - gv, 255 - bv

                pixels.append((rv, gv, bv))
            row += 1

    return width, height, pixels


def write_tiff(filename, width, height, pixels):
    """Write an uncompressed 24-bit RGB TIFF file. pixels is list of (R, G, B) tuples."""
    # We'll write a simple little-endian TIFF with one strip
    endian = '<'
    pixel_data = bytearray()
    for r, g, b in pixels:
        pixel_data += struct.pack('BBB', r, g, b)

    strip_size = len(pixel_data)

    # IFD will be after header (8 bytes) + pixel data
    pixel_offset = 8
    ifd_offset = pixel_offset + strip_size

    # Rational values (72/1 DPI) stored after IFD
    num_ifd_entries = 12
    ifd_size = 2 + num_ifd_entries * 12 + 4  # count + entries + next IFD ptr
    rational_offset = ifd_offset + ifd_size
    bps_offset = rational_offset + 16  # after two rationals (8 bytes each)

    with open(filename, 'wb') as f:
        # Header
        f.write(b'II')  # little-endian
        f.write(struct.pack('<H', 42))  # magic
        f.write(struct.pack('<I', ifd_offset))

        # Pixel data
        f.write(pixel_data)

        # IFD
        f.write(struct.pack('<H', num_ifd_entries))

        def write_ifd_entry(tag, type_id, count, value):
            f.write(struct.pack('<HHI', tag, type_id, count))
            if type_id == 3:  # SHORT
                f.write(struct.pack('<HH', value, 0))
            elif type_id == 4:  # LONG
                f.write(struct.pack('<I', value))
            else:
                f.write(struct.pack('<I', value))

        write_ifd_entry(_TIFF_IMAGE_WIDTH, 4, 1, width)
        write_ifd_entry(_TIFF_IMAGE_LENGTH, 4, 1, height)
        write_ifd_entry(_TIFF_BITS_PER_SAMPLE, 3, 3, bps_offset)  # offset to 3 shorts
        write_ifd_entry(_TIFF_COMPRESSION, 3, 1, 1)  # no compression
        write_ifd_entry(_TIFF_PHOTOMETRIC, 3, 1, 2)  # RGB
        write_ifd_entry(_TIFF_STRIP_OFFSETS, 4, 1, pixel_offset)
        write_ifd_entry(_TIFF_SAMPLES_PER_PIXEL, 3, 1, 3)
        write_ifd_entry(_TIFF_ROWS_PER_STRIP, 4, 1, height)
        write_ifd_entry(_TIFF_STRIP_BYTE_COUNTS, 4, 1, strip_size)
        write_ifd_entry(_TIFF_X_RESOLUTION, 5, 1, rational_offset)
        write_ifd_entry(_TIFF_Y_RESOLUTION, 5, 1, rational_offset + 8)
        write_ifd_entry(_TIFF_RESOLUTION_UNIT, 3, 1, 2)  # inches

        # Next IFD offset (0 = no more IFDs)
        f.write(struct.pack('<I', 0))

        # X resolution rational: 72/1
        f.write(struct.pack('<II', 72, 1))
        # Y resolution rational: 72/1
        f.write(struct.pack('<II', 72, 1))
        # BitsPerSample: 8, 8, 8
        f.write(struct.pack('<HHH', 8, 8, 8))


# ============================================================================
# Bitstream Writer (for encoding)
# ============================================================================

class BitWriter:
    """Writes bits to a bytearray, with JPEG byte-stuffing (0xFF -> 0xFF 0x00)."""

    def __init__(self):
        self.data = bytearray()
        self.current_byte = 0
        self.bit_pos = 7  # next bit position (7=MSB, 0=LSB)

    def write_bits(self, value, length):
        """Write `length` bits from `value` (MSB first)."""
        for i in range(length - 1, -1, -1):
            bit = (value >> i) & 1
            self.current_byte |= (bit << self.bit_pos)
            self.bit_pos -= 1
            if self.bit_pos < 0:
                self.data.append(self.current_byte)
                if self.current_byte == 0xFF:
                    self.data.append(0x00)  # byte stuffing
                self.current_byte = 0
                self.bit_pos = 7

    def flush(self):
        """Pad remaining bits with 1s and emit final byte."""
        if self.bit_pos < 7:
            # Pad with 1 bits
            self.current_byte |= ((1 << (self.bit_pos + 1)) - 1)
            self.data.append(self.current_byte)
            if self.current_byte == 0xFF:
                self.data.append(0x00)
            self.current_byte = 0
            self.bit_pos = 7


# ============================================================================
# Bitstream Reader (for decoding)
# ============================================================================

class BitReader:
    """Reads bits from JPEG scan data, handling byte-stuffing."""

    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.current_byte = 0
        self.bits_left = 0

    def _read_byte(self):
        """Read next byte, handling 0xFF 0x00 stuffing."""
        if self.pos >= len(self.data):
            return 0  # pad with zeros at end
        b = self.data[self.pos]
        self.pos += 1
        if b == 0xFF:
            if self.pos < len(self.data):
                next_b = self.data[self.pos]
                if next_b == 0x00:
                    self.pos += 1  # skip stuffed byte
                # If next_b is a marker (not 0x00), we've hit end of scan
        return b

    def read_bit(self):
        """Read a single bit."""
        if self.bits_left == 0:
            self.current_byte = self._read_byte()
            self.bits_left = 8
        self.bits_left -= 1
        return (self.current_byte >> self.bits_left) & 1

    def read_bits(self, n):
        """Read n bits as an unsigned integer."""
        value = 0
        for _ in range(n):
            value = (value << 1) | self.read_bit()
        return value


# ============================================================================
# Entropy Coding Helpers
# ============================================================================

def bit_length(value):
    """Number of bits needed to represent abs(value). 0 needs 0 bits."""
    if value == 0:
        return 0
    return abs(value).bit_length()


def encode_value(value):
    """Encode a value for JPEG: returns (category, bit_pattern).
    Positive values use their binary representation.
    Negative values use ones-complement."""
    if value == 0:
        return 0, 0
    cat = bit_length(value)
    if value > 0:
        return cat, value
    else:
        return cat, value + (1 << cat) - 1


def decode_value(category, bits):
    """Decode a JPEG-encoded value from category and bit pattern."""
    if category == 0:
        return 0
    if bits >= (1 << (category - 1)):
        return bits  # positive
    else:
        return bits - (1 << category) + 1  # negative


# ============================================================================
# JPEG Encoder
# ============================================================================

def encode_block(block_data, quant_table, prev_dc, dc_huff, ac_huff, writer):
    """Encode one 8x8 block: DCT -> quantize -> zigzag -> Huffman encode.
    Returns new DC value for differential coding."""
    # Level shift: subtract 128
    shifted = [float(v) - 128.0 for v in block_data]

    # Forward DCT
    dct = dct_2d(shifted)

    # Quantize
    quantized = quantize(dct, quant_table)

    # Zigzag scan
    zz = zigzag_scan(quantized)

    # DC coefficient (differential)
    dc_diff = zz[0] - prev_dc
    dc_cat, dc_bits = encode_value(dc_diff)

    # Write DC: Huffman code for category, then raw bits
    code, length = dc_huff[dc_cat]
    writer.write_bits(code, length)
    if dc_cat > 0:
        writer.write_bits(dc_bits, dc_cat)

    # AC coefficients
    zero_count = 0
    for i in range(1, 64):
        if zz[i] == 0:
            zero_count += 1
        else:
            # Emit ZRL (16 zeros) symbols if needed
            while zero_count >= 16:
                code, length = ac_huff[0xF0]  # ZRL
                writer.write_bits(code, length)
                zero_count -= 16

            ac_cat, ac_bits = encode_value(zz[i])
            rs = (zero_count << 4) | ac_cat
            code, length = ac_huff[rs]
            writer.write_bits(code, length)
            if ac_cat > 0:
                writer.write_bits(ac_bits, ac_cat)
            zero_count = 0

    # EOB if last coefficient(s) are zero
    if zero_count > 0:
        code, length = ac_huff[0x00]  # EOB
        writer.write_bits(code, length)

    return zz[0]


def jpeg_encode(width, height, pixels, quality=75):
    """Encode pixels (list of RGB tuples) to JPEG bytearray."""
    # Scale quantization tables
    lum_qt = scale_quant_table(STD_LUMINANCE_QUANT, quality)
    chr_qt = scale_quant_table(STD_CHROMINANCE_QUANT, quality)

    # Build Huffman encoding tables
    dc_lum_huff = build_huffman_encode_table(DC_LUMINANCE_BITS, DC_LUMINANCE_VALS)
    ac_lum_huff = build_huffman_encode_table(AC_LUMINANCE_BITS, AC_LUMINANCE_VALS)
    dc_chr_huff = build_huffman_encode_table(DC_CHROMINANCE_BITS, DC_CHROMINANCE_VALS)
    ac_chr_huff = build_huffman_encode_table(AC_CHROMINANCE_BITS, AC_CHROMINANCE_VALS)

    # Convert to YCbCr
    y_data = []
    cb_data = []
    cr_data = []
    for r, g, b in pixels:
        y, cb, cr = rgb_to_ycbcr(r, g, b)
        y_data.append(y)
        cb_data.append(cb)
        cr_data.append(cr)

    # Pad image to multiple of 8
    pad_w = (8 - width % 8) % 8
    pad_h = (8 - height % 8) % 8
    new_w = width + pad_w
    new_h = height + pad_h

    def pad_channel(data, w, h, new_w, new_h):
        """Pad a channel by replicating edge pixels."""
        padded = [0.0] * (new_w * new_h)
        for y in range(new_h):
            for x in range(new_w):
                sy = min(y, h - 1)
                sx = min(x, w - 1)
                padded[y * new_w + x] = data[sy * w + sx]
        return padded

    y_padded = pad_channel(y_data, width, height, new_w, new_h)
    cb_padded = pad_channel(cb_data, width, height, new_w, new_h)
    cr_padded = pad_channel(cr_data, width, height, new_w, new_h)

    def extract_block(data, bx, by, stride):
        """Extract 8x8 block starting at (bx*8, by*8)."""
        block = []
        for row in range(8):
            for col in range(8):
                block.append(data[(by * 8 + row) * stride + bx * 8 + col])
        return block

    # Encode scan data
    writer = BitWriter()
    prev_dc_y = 0
    prev_dc_cb = 0
    prev_dc_cr = 0

    blocks_x = new_w // 8
    blocks_y = new_h // 8

    for by in range(blocks_y):
        for bx in range(blocks_x):
            # Y block
            y_block = extract_block(y_padded, bx, by, new_w)
            prev_dc_y = encode_block(y_block, lum_qt, prev_dc_y,
                                     dc_lum_huff, ac_lum_huff, writer)
            # Cb block
            cb_block = extract_block(cb_padded, bx, by, new_w)
            prev_dc_cb = encode_block(cb_block, chr_qt, prev_dc_cb,
                                      dc_chr_huff, ac_chr_huff, writer)
            # Cr block
            cr_block = extract_block(cr_padded, bx, by, new_w)
            prev_dc_cr = encode_block(cr_block, chr_qt, prev_dc_cr,
                                      dc_chr_huff, ac_chr_huff, writer)

    writer.flush()
    scan_data = bytes(writer.data)

    # Build JPEG file
    out = bytearray()

    # SOI
    out += b'\xFF\xD8'

    # APP0 (JFIF)
    app0 = bytearray()
    app0 += b'JFIF\x00'      # identifier
    app0 += b'\x01\x01'       # version 1.1
    app0 += b'\x00'            # units: no units
    app0 += struct.pack('>HH', 1, 1)  # pixel aspect ratio
    app0 += b'\x00\x00'       # no thumbnail
    out += b'\xFF\xE0'
    out += struct.pack('>H', len(app0) + 2)
    out += app0

    # DQT (quantization tables)
    def write_dqt(table_id, table):
        dqt = bytearray()
        dqt.append(table_id)  # 0=8-bit precision, lower nibble=table ID
        for i in range(64):
            dqt.append(table[ZIGZAG_ORDER[i]])
        out_bytes = b'\xFF\xDB'
        out_bytes += struct.pack('>H', len(dqt) + 2)
        out_bytes += bytes(dqt)
        return out_bytes

    out += write_dqt(0, lum_qt)
    out += write_dqt(1, chr_qt)

    # SOF0 (Start of Frame — baseline DCT)
    sof = bytearray()
    sof.append(8)  # precision
    sof += struct.pack('>HH', height, width)
    sof.append(3)  # number of components
    # Component 1 (Y): ID=1, sampling=1x1, quant table 0
    sof += b'\x01\x11\x00'
    # Component 2 (Cb): ID=2, sampling=1x1, quant table 1
    sof += b'\x02\x11\x01'
    # Component 3 (Cr): ID=3, sampling=1x1, quant table 1
    sof += b'\x03\x11\x01'
    out += b'\xFF\xC0'
    out += struct.pack('>H', len(sof) + 2)
    out += sof

    # DHT (Huffman tables)
    def write_dht(table_class, table_id, bits, vals):
        dht = bytearray()
        dht.append((table_class << 4) | table_id)
        for i in range(1, 17):
            dht.append(bits[i])
        for v in vals:
            dht.append(v)
        out_bytes = b'\xFF\xC4'
        out_bytes += struct.pack('>H', len(dht) + 2)
        out_bytes += bytes(dht)
        return out_bytes

    out += write_dht(0, 0, DC_LUMINANCE_BITS, DC_LUMINANCE_VALS)     # DC lum
    out += write_dht(0, 1, DC_CHROMINANCE_BITS, DC_CHROMINANCE_VALS)  # DC chr
    out += write_dht(1, 0, AC_LUMINANCE_BITS, AC_LUMINANCE_VALS)     # AC lum
    out += write_dht(1, 1, AC_CHROMINANCE_BITS, AC_CHROMINANCE_VALS)  # AC chr

    # SOS (Start of Scan)
    sos = bytearray()
    sos.append(3)  # number of components
    sos += b'\x01\x00'  # Y: DC table 0, AC table 0
    sos += b'\x02\x11'  # Cb: DC table 1, AC table 1
    sos += b'\x03\x11'  # Cr: DC table 1, AC table 1
    sos += b'\x00\x3F\x00'  # spectral selection 0-63, successive approx 0
    out += b'\xFF\xDA'
    out += struct.pack('>H', len(sos) + 2)
    out += sos

    # Scan data
    out += scan_data

    # EOI
    out += b'\xFF\xD9'

    return bytes(out)


# ============================================================================
# JPEG Decoder
# ============================================================================

class JPEGDecoder:
    """Baseline JPEG decoder."""

    def __init__(self):
        self.width = 0
        self.height = 0
        self.quant_tables = {}
        self.huff_dc = {}  # table_id -> decode entries
        self.huff_ac = {}
        self.components = []  # list of component info dicts
        self.scan_data = None

    def decode_file(self, filename):
        """Decode a JPEG file to (width, height, pixels)."""
        with open(filename, 'rb') as f:
            data = f.read()
        return self.decode_bytes(data)

    def decode_bytes(self, data):
        """Decode JPEG bytes to (width, height, pixels)."""
        pos = 0

        if data[0:2] != b'\xFF\xD8':
            raise ValueError("Not a JPEG file (missing SOI)")

        pos = 2
        while pos < len(data):
            if data[pos] != 0xFF:
                raise ValueError(f"Expected marker at pos {pos}, got 0x{data[pos]:02X}")

            # Skip padding FF bytes
            while pos < len(data) - 1 and data[pos + 1] == 0xFF:
                pos += 1

            marker = data[pos + 1]
            pos += 2

            if marker == 0xD9:  # EOI
                break

            if marker == 0xD8:  # SOI (shouldn't appear again)
                continue

            # Read segment length
            seg_len = struct.unpack('>H', data[pos:pos+2])[0]
            seg_data = data[pos+2:pos+seg_len]

            if marker == 0xE0:  # APP0
                pass  # skip JFIF header

            elif marker in (0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7,
                            0xE8, 0xE9, 0xEA, 0xEB, 0xEC, 0xED, 0xEE, 0xEF):
                pass  # skip other APP markers

            elif marker == 0xFE:  # COM (comment)
                pass

            elif marker == 0xDB:  # DQT
                self._parse_dqt(seg_data)

            elif marker == 0xC0:  # SOF0 (baseline)
                self._parse_sof(seg_data)

            elif marker == 0xC4:  # DHT
                self._parse_dht(seg_data)

            elif marker == 0xDA:  # SOS
                self._parse_sos_header(seg_data)
                pos += seg_len
                # Everything after SOS header until next marker is scan data
                scan_start = pos
                # Find end of scan: look for 0xFF followed by non-zero, non-0x00
                scan_end = scan_start
                while scan_end < len(data) - 1:
                    if data[scan_end] == 0xFF and data[scan_end + 1] != 0x00:
                        if data[scan_end + 1] != 0xFF:  # not padding
                            break
                    scan_end += 1
                self.scan_data = data[scan_start:scan_end]
                pos = scan_end
                continue

            pos += seg_len

        # Decode the scan
        return self._decode_scan()

     def _parse_dqt(self, data):
        """
        Parse DQT segment.

        JPEG stores quantization table entries in zigzag order. Internally this
        decoder uses natural row-major 8x8 order, so the table must be unzigzagged
        after reading.
        """
        pos = 0

        while pos < len(data):
            info = data[pos]
            precision = (info >> 4) & 0x0F  # 0=8-bit, 1=16-bit
            table_id = info & 0x0F
            pos += 1

            if precision == 0:
                if pos + 64 > len(data):
                    raise ValueError("Truncated DQT segment")

                # Values are stored in JPEG zigzag order.
                raw_table = list(data[pos:pos + 64])
                pos += 64

            elif precision == 1:
                if pos + 128 > len(data):
                    raise ValueError("Truncated 16-bit DQT segment")

                # Values are stored in JPEG zigzag order.
                raw_table = [
                    struct.unpack('>H', data[pos + i * 2:pos + i * 2 + 2])[0]
                    for i in range(64)
                ]
                pos += 128

            else:
                raise ValueError(f"Unsupported DQT precision: {precision}")

            # Critical fix:
            # Convert from JPEG zigzag order back to natural row-major order.
            self.quant_tables[table_id] = zigzag_unscan(raw_table)
                
    def _parse_sof(self, data):
        """Parse SOF0 segment."""
        precision = data[0]
        self.height = struct.unpack('>H', data[1:3])[0]
        self.width = struct.unpack('>H', data[3:5])[0]
        num_components = data[5]
        self.components = []
        pos = 6
        for _ in range(num_components):
            comp_id = data[pos]
            sampling = data[pos + 1]
            h_samp = (sampling >> 4) & 0x0F
            v_samp = sampling & 0x0F
            qt_id = data[pos + 2]
            self.components.append({
                'id': comp_id,
                'h_samp': h_samp,
                'v_samp': v_samp,
                'qt_id': qt_id,
            })
            pos += 3

    def _parse_dht(self, data):
        """Parse DHT segment."""
        pos = 0
        while pos < len(data):
            info = data[pos]
            table_class = (info >> 4) & 0x0F  # 0=DC, 1=AC
            table_id = info & 0x0F
            pos += 1
            bits = [0] + list(data[pos:pos+16])
            pos += 16
            total = sum(bits[1:])
            vals = list(data[pos:pos+total])
            pos += total

            entries = build_huffman_decode_table(bits, vals)
            if table_class == 0:
                self.huff_dc[table_id] = entries
            else:
                self.huff_ac[table_id] = entries

    def _parse_sos_header(self, data):
        """Parse SOS header (component-to-table mappings)."""
        num_components = data[0]
        self.scan_components = []
        pos = 1
        for _ in range(num_components):
            comp_id = data[pos]
            tables = data[pos + 1]
            dc_table = (tables >> 4) & 0x0F
            ac_table = tables & 0x0F
            self.scan_components.append({
                'id': comp_id,
                'dc_table': dc_table,
                'ac_table': ac_table,
            })
            pos += 2

    def _huffman_decode(self, reader, entries):
        """Decode one Huffman symbol from the bitstream.
        Uses min-code lookup for O(1) per length instead of linear scan."""
        code = 0
        for length in range(1, 17):
            code = (code << 1) | reader.read_bit()
            # Find matching entry at this length
            for entry_code, entry_len, entry_val in entries:
                if entry_len == length and entry_code == code:
                    return entry_val
                if entry_len > length:
                    break  # entries are sorted by length, skip ahead
        raise ValueError("Huffman decode failed — no matching code")

    def _decode_block(self, reader, quant_table, dc_entries, ac_entries, prev_dc):
        """Decode one 8x8 block from the bitstream."""
        # DC coefficient
        dc_cat = self._huffman_decode(reader, dc_entries)
        if dc_cat > 0:
            dc_bits = reader.read_bits(dc_cat)
            dc_diff = decode_value(dc_cat, dc_bits)
        else:
            dc_diff = 0
        dc_val = prev_dc + dc_diff

        # AC coefficients
        zz = [0] * 64
        zz[0] = dc_val
        i = 1
        while i < 64:
            rs = self._huffman_decode(reader, ac_entries)
            if rs == 0x00:  # EOB
                break
            elif rs == 0xF0:  # ZRL (16 zeros)
                i += 16
            else:
                run = (rs >> 4) & 0x0F
                cat = rs & 0x0F
                i += run
                if i >= 64:
                    break
                if cat > 0:
                    bits = reader.read_bits(cat)
                    zz[i] = decode_value(cat, bits)
                i += 1

        # Inverse zigzag
        block = zigzag_unscan(zz)

        # Dequantize
        block = dequantize(block, quant_table)

        # Inverse DCT
        block = idct_2d(block)

        # Level shift: add 128
        block = [v + 128.0 for v in block]

        return block, dc_val

    def _decode_scan(self):
        """Decode the scan data into pixels. Handles arbitrary chroma subsampling."""
        reader = BitReader(self.scan_data)

        # Determine max sampling factors
        comp_info = {c['id']: c for c in self.components}
        max_h = max(c['h_samp'] for c in self.components)
        max_v = max(c['v_samp'] for c in self.components)

        # MCU dimensions in pixels
        mcu_w = max_h * 8
        mcu_h = max_v * 8

        # Number of MCUs
        mcus_x = (self.width + mcu_w - 1) // mcu_w
        mcus_y = (self.height + mcu_h - 1) // mcu_h

        # Full padded size
        full_w = mcus_x * mcu_w
        full_h = mcus_y * mcu_h

        # Allocate channels at their native resolution
        # Y channel: full resolution
        # Cb/Cr channels: may be subsampled
        channels = {}
        for comp in self.components:
            cid = comp['id']
            ch_w = mcus_x * comp['h_samp'] * 8
            ch_h = mcus_y * comp['v_samp'] * 8
            channels[cid] = {
                'data': [0.0] * (ch_w * ch_h),
                'width': ch_w,
                'height': ch_h,
                'h_samp': comp['h_samp'],
                'v_samp': comp['v_samp'],
            }

        sc = self.scan_components
        prev_dc = {sc_comp['id']: 0 for sc_comp in sc}

        for mcu_y in range(mcus_y):
            for mcu_x in range(mcus_x):
                for sc_comp in sc:
                    cid = sc_comp['id']
                    comp = comp_info[cid]
                    qt = self.quant_tables[comp['qt_id']]
                    dc_entries = self.huff_dc[sc_comp['dc_table']]
                    ac_entries = self.huff_ac[sc_comp['ac_table']]
                    ch = channels[cid]

                    # Each component has h_samp * v_samp blocks per MCU
                    for sv in range(comp['v_samp']):
                        for sh in range(comp['h_samp']):
                            block, prev_dc[cid] = self._decode_block(
                                reader, qt, dc_entries, ac_entries, prev_dc[cid])

                            # Write block to channel at native resolution
                            bx = mcu_x * comp['h_samp'] + sh
                            by = mcu_y * comp['v_samp'] + sv
                            for row in range(8):
                                for col in range(8):
                                    px = bx * 8 + col
                                    py = by * 8 + row
                                    if px < ch['width'] and py < ch['height']:
                                        ch['data'][py * ch['width'] + px] = block[row * 8 + col]

        # Convert YCbCr to RGB, upsampling chroma as needed
        # Component IDs: 1=Y, 2=Cb, 3=Cr (standard JFIF)
        y_ch = channels.get(1, channels.get(sc[0]['id']))
        cb_ch = channels.get(2, channels.get(sc[1]['id'])) if len(sc) > 1 else None
        cr_ch = channels.get(3, channels.get(sc[2]['id'])) if len(sc) > 2 else None

        pixels = []
        for py in range(self.height):
            for px in range(self.width):
                # Y is at full resolution
                y_idx = py * y_ch['width'] + px
                yv = y_ch['data'][y_idx] if y_idx < len(y_ch['data']) else 128.0

                if cb_ch and cr_ch:
                    # Scale pixel coords to chroma channel coords
                    cb_x = px * cb_ch['h_samp'] // max_h
                    cb_y = py * cb_ch['v_samp'] // max_v
                    cb_idx = cb_y * cb_ch['width'] + cb_x
                    cb = cb_ch['data'][cb_idx] if cb_idx < len(cb_ch['data']) else 128.0

                    cr_x = px * cr_ch['h_samp'] // max_h
                    cr_y = py * cr_ch['v_samp'] // max_v
                    cr_idx = cr_y * cr_ch['width'] + cr_x
                    cr = cr_ch['data'][cr_idx] if cr_idx < len(cr_ch['data']) else 128.0

                    r, g, b = ycbcr_to_rgb(yv, cb, cr)
                else:
                    r, g, b = int(round(yv)), int(round(yv)), int(round(yv))

                pixels.append((r, g, b))

        return self.width, self.height, pixels


# ============================================================================
# Main CLI
# ============================================================================

def read_image(filename):
    """Auto-detect image format and read. Supports BMP and TIFF."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in ('tif', 'tiff'):
        return read_tiff(filename), 'TIFF'
    elif ext == 'bmp':
        return read_bmp(filename), 'BMP'
    else:
        # Try to detect by magic bytes
        with open(filename, 'rb') as f:
            magic = f.read(4)
        if magic[:2] == b'BM':
            return read_bmp(filename), 'BMP'
        elif magic[:2] in (b'II', b'MM'):
            return read_tiff(filename), 'TIFF'
        else:
            raise ValueError(f"Unknown image format: {filename}")


def write_image(filename, width, height, pixels):
    """Auto-detect output format by extension. Supports BMP and TIFF."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in ('tif', 'tiff'):
        write_tiff(filename, width, height, pixels)
        return 'TIFF'
    else:
        write_bmp(filename, width, height, pixels)
        return 'BMP'


def main():
    parser = argparse.ArgumentParser(description="Pure-Python JPEG Codec")
    sub = parser.add_subparsers(dest="command")

    enc = sub.add_parser("encode", help="Encode BMP/TIFF to JPEG")
    enc.add_argument("input", help="Input image file (BMP or TIFF)")
    enc.add_argument("output", help="Output JPEG file")
    enc.add_argument("--quality", type=int, default=75, help="Quality 1-100 (default 75)")

    dec = sub.add_parser("decode", help="Decode JPEG to BMP/TIFF")
    dec.add_argument("input", help="Input JPEG file")
    dec.add_argument("output", help="Output image file (BMP or TIFF, based on extension)")

    args = parser.parse_args()

    if args.command == "encode":
        (w, h, pixels), fmt = read_image(args.input)
        print(f"Read {fmt}: {args.input} ({w}x{h})")
        print(f"Encoding JPEG (quality={args.quality})...")
        jpeg_data = jpeg_encode(w, h, pixels, quality=args.quality)
        with open(args.output, 'wb') as f:
            f.write(jpeg_data)
        print(f"Written: {args.output} ({len(jpeg_data)} bytes)")

    elif args.command == "decode":
        print(f"Reading JPEG: {args.input}")
        decoder = JPEGDecoder()
        w, h, pixels = decoder.decode_file(args.input)
        print(f"Image: {w}x{h}")
        fmt = write_image(args.output, w, h, pixels)
        print(f"Written {fmt}: {args.output}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
