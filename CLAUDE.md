# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Pure-Python JPEG codec (encoder + decoder) with zero external dependencies — stdlib only. Implements baseline JPEG (JFIF) with 4:4:4 chroma (no subsampling). Produces files compatible with standard decoders (browsers, ImageMagick, etc).

## Commands

```bash
# Encode BMP/TIFF to JPEG
python jpeg_codec.py encode input.bmp output.jpg --quality 75

# Decode JPEG to BMP/TIFF (format chosen by output extension)
python jpeg_codec.py decode input.jpg output.bmp
python jpeg_codec.py decode input.jpg output.tif

# Generate a 128x128 rainbow test image
python generate_test_bmp.py
```

Note: `generate_test_bmp.py` has a hardcoded output path that may need updating.

## Architecture

Everything lives in `jpeg_codec.py` (~1300 lines), organized as a single-file pipeline:

**Encoding pipeline:** RGB pixels → YCbCr → 8x8 blocks (edge-padded) → DCT → quantization → zigzag scan → Huffman coding → JFIF byte assembly

**Decoding pipeline** (`JPEGDecoder` class): JFIF marker parsing → Huffman decode → inverse zigzag → dequantization → IDCT → YCbCr→RGB

Key design decisions:
- Encoder is functional (standalone functions); decoder is a class (`JPEGDecoder`) that accumulates state from parsed markers
- Uses standard JPEG Huffman tables (Annex K) — no optimized/custom tables
- Quantization scaling uses the libjpeg formula
- `BitWriter`/`BitReader` handle JPEG byte-stuffing (0xFF→0xFF 0x00)
- Image I/O supports both 24-bit BMP and uncompressed TIFF, with auto-detection by extension or magic bytes
- DCT uses a precomputed cosine table (`_COS_TABLE`) but is otherwise a straightforward O(N^3) implementation per 8x8 block
