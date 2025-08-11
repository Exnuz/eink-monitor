#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
epd_wrapper.py
Lightweight wrapper around epd2in13_V3 to provide:
- init_full(), clear(), display_full(), set_base(), display_partial()
- automatic handling of orientation and PIL image -> buffer conversion
Requires: epd2in13_V3.py and epdconfig.py in the same package (waveshare_epd)
"""
from PIL import Image
import logging
from waveshare_epd import epd2in13_V3 as raw_driver

logger = logging.getLogger(__name__)

class EPDWrapper:
    def __init__(self, orientation="portrait"):
        """
        orientation: "portrait" or "landscape"
        """
        self._drv = raw_driver.EPD()
        self.orientation = orientation.lower()
        # width/height from driver
        self.width = self._drv.width
        self.height = self._drv.height
        # computed image size depending on orientation
        self._set_img_size()

    def _set_img_size(self):
        if self.orientation == "portrait":
            self.img_w, self.img_h = self.width, self.height
        else:
            self.img_w, self.img_h = self.height, self.width

    def init_full(self):
        """Init hardware and perform default full LUT; keep device ready."""
        if self._drv.init() != 0:
            raise RuntimeError("EPD module init failed")
        # driver init already sets LUT full update
        return

    def clear(self, color=0xFF):
        """Clear screen (color byte) — driver expects 0xFF white, 0x00 black"""
        # The driver's Clear expects a single byte parameter
        self._drv.Clear(color)

    def sleep(self):
        self._drv.sleep()

    def _normalize_image(self, image):
        """
        Accepts PIL.Image. Returns buffer bytes expected by driver's display/displayPartial.
        Handles orientation (rotate 90 deg if needed) and conversion to '1'.
        """
        if not isinstance(image, Image.Image):
            raise TypeError("image must be PIL.Image")

        imw, imh = image.size
        # If image matches driver widthxheight, convert
        if (imw, imh) == (self.img_w, self.img_h):
            img = image.convert('1')
        elif (imw, imh) == (self.img_h, self.img_w):
            # rotated image provided; rotate to driver's orientation
            img = image.rotate(90, expand=True).convert('1')
        else:
            logger.warning("Image has wrong dimensions: expected %sx%s or %sx%s, got %sx%s" %
                           (self.img_w, self.img_h, self.img_h, self.img_w, imw, imh))
            # create blank
            img = Image.new('1', (self.img_w, self.img_h), 255)

        # epd2in13_V3.getbuffer returns bytearray from raw bytes; reuse it
        buf = self._drv.getbuffer(img)
        return buf

    # Full display (single buffer)
    def display_full(self, pil_image):
        buf = self._normalize_image(pil_image)
        # driver.display expects image buffer (single)
        self._drv.display(buf)

    # Methods for partial update workflow
    def set_base(self, pil_image):
        """Set base image in RAM so that subsequent partial updates work against it."""
        buf = self._normalize_image(pil_image)
        self._drv.displayPartBaseImage(buf)

    def display_partial(self, pil_image):
        """Partial update with provided image buffer (same size as full)."""
        buf = self._normalize_image(pil_image)
        self._drv.displayPartial(buf)

    # Convenience: prepare blank images for drawing
    def new_image(self):
        from PIL import Image
        return Image.new('1', (self.img_w, self.img_h), 255)
