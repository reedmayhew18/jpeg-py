# 👑 JPEG-Py - The JPEG-EALOUS Queen of Python Codecs

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![JPEG](https://img.shields.io/badge/JPEG-baseline%20compliant-orange.svg)
![Dependencies](https://img.shields.io/badge/dependencies-literally%20zero-pink.svg)

A delusionally ambitious, pure Python implementation of the [JPEG](https://www.w3.org/Graphics/JPEG/) baseline codec. No NumPy. No Pillow. No OpenCV. Just `math`, `struct`, and unhinged determination. We implemented DCT by hand because we hate ourselves.

## 🤷‍♂️ What is This?

A full JPEG encoder AND decoder written in pure Python stdlib. She reads your BMP, she reads your TIFF, she crunches them through a hand-rolled DCT, quantizes them with the same tables libjpeg uses, Huffman-codes them according to the actual JPEG spec (Annex K, look it up), and spits out a `.jpg` file that every browser, viewer, and image tool on the planet will open without complaint.

Then she'll decode it back too. She's versatile like that.

- **Lossy** - Your pixels go in looking like a 10, they come out looking like a solid 7. That's the JPEG promise.
- **Spec Compliant** - She follows the ITU-T T.81 standard. Yes, we read it. Yes, it was 186 pages. Yes, we need therapy.
- **Zero Dependencies** - Not even Pillow. We wrote our own BMP parser. We wrote our own TIFF parser. We are unwell.
- **"Why Would You Do This?"** - Because someone had to prove Python can do lossy compression without calling out to C. That someone was us.

## 💅 The Glow Up (Features)

- ✅ **Full Baseline JPEG**: DCT, quantization, zigzag, Huffman — the whole runway.
- ✅ **Absolutely Zero Dependencies**: We didn't just kick NumPy out of the house, we never even let her in. Pure stdlib. `math` and `struct` are doing ALL the heavy lifting.
- ✅ **Quality Control**: Quality 1–100, scaled with the libjpeg formula. Crank it to 100 for pixel perfection or drop it to 10 for that vintage surveillance camera aesthetic.
- ✅ **BMP & TIFF I/O**: She reads and writes both, with auto-detection by extension or magic bytes. Versatile queen.
- ✅ **Spec-Legal Huffman Tables**: Straight from JPEG Annex K. We didn't improvise, we studied.
- ✅ **YCbCr Color Space**: She converts your RGB to luminance and chrominance like a proper signal processing girlboss.
- ✅ **Byte Stuffing**: 0xFF becomes 0xFF 0x00 in the scan data because the spec said so and we don't ask questions.

## 📦 Installation

```bash
# Clone the cathedral of suffering
git clone https://github.com/reedmayhew18/jpeg-py.git
cd jpeg-py

# Install dependencies
# Just kidding. There aren't any. She came with nothing and built an empire.
```

## 🚀 Usage

### Command Line Runway

```bash
# Encode a BMP to JPEG (default quality 75)
python jpeg_codec.py encode photo.bmp photo.jpg

# Encode with maximum quality (for when you care too much)
python jpeg_codec.py encode photo.bmp photo.jpg --quality 100

# Encode with minimum quality (for when you simply don't)
python jpeg_codec.py encode photo.bmp photo.jpg --quality 10

# Encode from TIFF because we support that too, you're welcome
python jpeg_codec.py encode photo.tif photo.jpg

# Decode back to BMP
python jpeg_codec.py decode photo.jpg photo.bmp

# Decode to TIFF because variety is the spice of life
python jpeg_codec.py decode photo.jpg photo.tif
```

### Generate a Test Image

```bash
# Create a 128x128 rainbow gradient BMP (also pure Python, obviously)
python generate_test_bmp.py
```

## 👠 Performance

She's doing the Discrete Cosine Transform in a `for` loop. In Python. Let that sink in.

Every single 8x8 block goes through a full 2D DCT with precomputed cosine tables. That's 64 multiply-accumulates per coefficient, 64 coefficients per block, three color channels. In an interpreted language. She's not fast, but she is *correct*, and honestly that's more than most people can say about themselves.

- **Encoding**: Each 8x8 block gets the full spa treatment — level shift, DCT, quantization, zigzag, Huffman. It's "meditative."
- **Decoding**: Parses JFIF markers, rebuilds Huffman trees, inverse-DCTs every block. She's thorough.
- **Memory**: We precompute the cosine table once and reuse it. That's our version of optimization. We're proud of it.

**Benchmarks:**
*"She's serving frequency-domain realness, not frame rate."*
- **128x128 RGB**: A few seconds (She's warming up)
- **512x512 RGB**: Go make coffee (She's contemplating the cosine of existence)

## 🔧 Implementation Tea

The entire JPEG pipeline, in one file, because modularity is for cowards:

1. **Hand-Rolled DCT**: A 2D separable DCT using precomputed `cos((2x+1)uπ/16)` values. We literally typed out the math.
2. **Quantization with the libjpeg Formula**: `scale = quality < 50 ? 5000/q : 200-2q`. We scale the standard tables. She's calibrated.
3. **Zigzag Scanning**: That iconic diagonal traversal pattern. We hardcoded all 64 indices because we believe in commitment.
4. **Huffman Coding**: We build encoding AND decoding tables from the JPEG standard bit counts. Both directions. She's bilateral.
5. **BitWriter/BitReader**: Custom bitstream classes that handle JPEG byte-stuffing. Every 0xFF gets a 0x00 chaperone. Safety first.
6. **BMP & TIFF Parsers**: We wrote TWO image format parsers from scratch using `struct.unpack`. We could have used Pillow. We chose violence.

## 📝 License

MIT License — Because lossy compression should be free, even if writing it cost us our sanity.

## 🙏 Acknowledgments

- The JPEG Committee for creating a compression standard that has survived since 1992. Legends.
- The libjpeg developers for the quantization scaling formula we shamelessly adopted.
- The authors of ITU-T T.81 for a 186-page spec that we actually read. Some of it. Most of it. Enough of it.
- [QOI-Py](https://github.com/reedmayhew18/qoi-py), our sister project, for proving that pure-Python image codecs are a valid lifestyle choice.

## ⚠️ Disclaimer

**This is a Python script doing the Discrete Cosine Transform in nested for-loops.**

Do not use this for:
- Batch processing thousands of photos.
- Anything time-sensitive.
- Your production pipeline (please).
- Impressing anyone who has ever opened `libjpeg-turbo` source code.

Do use this for:
- Understanding how JPEG actually works under the hood.
- Proving Python can implement any algorithm if you simply refuse to give up.
- Generating artisanal, hand-crafted, locally-sourced JPEG files.
- The vibes.

---

*Remember: We didn't just implement JPEG in Python. We implemented the BMP parser, the TIFF parser, the DCT, the Huffman coder, AND the bitstream handler. In one file. With zero imports beyond stdlib. This wasn't a project, it was a cry for help.* ✨
