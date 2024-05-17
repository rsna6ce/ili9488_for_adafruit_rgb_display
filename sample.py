import time
from busio import SPI
from board import SCK, MOSI, MISO, D8, D18, D23, D24, D2, D3
from digitalio import DigitalInOut, Direction
from PIL import Image
from adafruit_rgb_display.rgb import color565
from adafruit_rgb_display.ili9488 import ILI9488

try:
    img = Image.open("sample.png")
except:
    img = None

# Configuration for GPIO pins:
CS_PIN    = DigitalInOut(D8)
LED_PIN   = DigitalInOut(D18)
RESET_PIN = DigitalInOut(D23)
DC_PIN    = DigitalInOut(D24)

LED_PIN.direction = Direction.OUTPUT

# Setup SPI bus using hardware SPI:
spi = SPI(clock=SCK, MOSI=MOSI, MISO=MISO)

# Create the ILI9488 display:
display = ILI9488(spi, cs=CS_PIN, dc=DC_PIN, rst=RESET_PIN, rotation=0, baudrate=40000000)
# In raspberry pi3 environment, the baudrate may be increased to 50000000 Hz

# Turn on & off backlight:
display.fill(color565((255,255,255)))
LED_PIN.value = True
time.sleep(1)
LED_PIN.value = False
time.sleep(1)
LED_PIN.value = True

# Main loop:
while True:
    # Clear the display
    display.fill(0)
    print("clear display")
    # Draw a red pixel in the center.
    display.pixel(display.width // 2, display.height // 2, color565(255, 0, 0))
    # Pause 1 seconds.
    time.sleep(1)
    # Fill the screen red, green, blue, then black:
    for color in ((255, 0, 0), (0, 255, 0), (0, 0, 255)):
        display.fill(color565(color))
    # Draw image
    if img:
        display.image(img)
        time.sleep(1)
