# SPDX-FileCopyrightText: 2017 Radomir Dopieralski for Adafruit Industries
# SPDX-FileCopyrightText: 2023 Matt Land
# SPDX-FileCopyrightText: 2024 Masahiro Konishi
#
# SPDX-License-Identifier: MIT

"""
`adafruit_rgb_display.ili9488`
====================================================

A simple driver for the ILI9488-based displays.

* Author(s): Radomir Dopieralski, Michael McWethy, Matt Land, Masahiro Konishi
"""
import struct

from adafruit_rgb_display.rgb import DisplaySPI, color565

try:
    from typing import Optional, Union, Tuple
    import digitalio
    import busio
    from circuitpython_typing.pil import Image
except ImportError:
    pass

try:
    import numpy
except ImportError:
    numpy = None

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_RGB_Display.git"


class ILI9488(DisplaySPI):
    """
    A simple driver for the ILI9488-based displays.

    >>> import busio
    >>> import digitalio
    >>> import board
    >>> from adafruit_rgb_display import color565
    >>> import adafruit_rgb_display.ili9488 as ili9488
    >>> spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    >>> display = ili9488.ILI9488(spi, cs=digitalio.DigitalInOut(board.GPIO0),
    ...    dc=digitalio.DigitalInOut(board.GPIO15))
    >>> display.fill(color565(0xff, 0x11, 0x22))
    >>> display.pixel(120, 160, 0)
    """

    _COLUMN_SET = 0x2A
    _PAGE_SET = 0x2B
    _RAM_WRITE = 0x2C
    _RAM_READ = 0x2E
    _INIT = (
        # PGAMCTRL (Positive Gamma Control)
        (0xE0, b"\x00\x03\x09\x08\x16\x0A\x3F\x78\x4C\x09\x0A\x08\x16\x1A\x0F"),
        # NGAMCTRL (Negative Gamma Control)
        (0xE1, b"\x00\x16\x19\x03\x0F\x05\x32\x45\x46\x04\x0E\x0D\x35\x37\x0F"),
        # Power Control 1
        (0xC0, b"\x17\x15"),
        # Power Control 2
        (0xC1, b"\x41"),
        # VCOM Control 1
        (0xC5, b"\x00\x12\x80"),
        # Memory Access Control
        # | MY | MX | MV | ML | BGR | MH | x | x |
        # |  0 |  1 |  0 |  0 |   1 |  0 | 0 | 0 |
        (0x36, b"\x48"),
        # Interface Pixel Format
        (0x3A, b"\x66"),  # 18bit; DPI = 6, DBI = 6
        # Interface Mode Control
        (0xB0, b"\x80"),  # SDA_EN = 1
        # Frame Rate Control (In Normal Mode/Full Colors)
        (0xB1, b"\xA0"),  # FRS = 10, DIVA = 0
        # Display Inversion Control
        (0xB4, b"\x02"),  # 2-dot; DINV = 2
        # Display Function Control
        (0xB6, b"\x02\x02"),
        # Set Image Function
        (0xE9, b"\x00"),
        # Adjust Control 3
        (0xF7, b"\xA9\x51\x2C\x82"),

        # Sleep OUT
        (0x11, None),
        # Display ON
        (0x29, None),
    )
    _ENCODE_PIXEL = None
    _ENCODE_POS = ">HH"
    _DECODE_PIXEL = ">BBB"

    # pylint: disable-msg=too-many-arguments
    def __init__(
        self,
        spi: busio.SPI,
        dc: digitalio.DigitalInOut,
        cs: digitalio.DigitalInOut,
        rst: Optional[digitalio.DigitalInOut] = None,
        width: int = 320,
        height: int = 480,
        baudrate: int = 16000000,
        polarity: int = 0,
        phase: int = 0,
        rotation: int = 0,
    ):
        super().__init__(
            spi,
            dc,
            cs,
            rst=rst,
            width=width,
            height=height,
            baudrate=baudrate,
            polarity=polarity,
            phase=phase,
            rotation=rotation,
        )
        self._scroll = 0

    # pylint: enable-msg=too-many-arguments

    def _encode_pixel(self, color: Union[int, Tuple]) -> bytes:
        """Encode a pixel color into bytes."""
        assert type(color) is int
        r = (((color & 0b1111_1000_0000_0000) >> 11) * 255) // 31
        g = (((color & 0b0000_0111_1110_0000) >>  5) * 255) // 63
        b = (((color & 0b0000_0000_0001_1111)      ) * 255) // 31
        return struct.pack(">BBB", r, g, b)

    def image(
        self,
        img: Image,
        rotation: Optional[int] = None,
        x: int = 0,
        y: int = 0,
    ) -> None:
        """Set buffer to value of Python Imaging Library image. The image should
        be in 1 bit mode and a size not exceeding the display size when drawn at
        the supplied origin."""
        if rotation is None:
            rotation = self.rotation
        if not img.mode in ("RGB", "RGBA"):
            raise ValueError("Image must be in mode RGB or RGBA")
        if rotation not in (0, 90, 180, 270):
            raise ValueError("Rotation must be 0/90/180/270")
        if rotation != 0:
            img = img.rotate(rotation, expand=True)
        imwidth, imheight = img.size
        if x + imwidth > self.width or y + imheight > self.height:
            raise ValueError(
                "Image must not exceed dimensions of display ({0}x{1}).".format(
                    self.width, self.height
                )
            )
        if numpy:
            data = numpy.array(img.convert("RGB")).astype("uint16")
            data[:, :, 0] = ((data[:, :, 0] >> 3) * 255) // 31
            data[:, :, 1] = ((data[:, :, 1] >> 2) * 255) // 63
            data[:, :, 2] = ((data[:, :, 2] >> 3) * 255) // 31
            pixels = bytes(data.flatten().astype("uint8"))
        else:
            # Slower but doesn't require numpy
            pixels = bytearray(imwidth * imheight * 3)
            for i in range(imwidth):
                for j in range(imheight):
                    pix = color565(img.getpixel((i, j)))
                    pixels[3 * (j * imwidth + i)] = (((pix & 0b1111_1000_0000_0000) >> 11) * 255) // 31
                    pixels[3 * (j * imwidth + i) + 1] = (((pix & 0b0000_0111_1110_0000) >>  5) * 255) // 63
                    pixels[3 * (j * imwidth + i) + 2] = (((pix & 0b0000_0000_0001_1111)      ) * 255) // 31
        self._block(x, y, x + imwidth - 1, y + imheight - 1, pixels)

    def scroll(
        self, dy: Optional[int] = None  # pylint: disable-msg=invalid-name
    ) -> Optional[int]:
        """Scroll the display by delta y"""
        if dy is None:
            return self._scroll
        self._scroll = (self._scroll + dy) % self.height
        self.write(0x37, struct.pack(">H", self._scroll))
        return None
