#!/usr/bin/python

##  This file is part of psbuffer.
##
##  Copyright 2006–23 by Diedrich Vorberg <diedrich@tux4web.de>
##
##  All Rights Reserved
##
##  For more Information on orm see the README file.
##
##  This program is free software; you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation; either version 2 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program; if not, write to the Free Software
##  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
##
##  I have added a copy of the GPL in the file gpl.txt.

def rgb(r, g, b):
    """
    Each color is a float 0 <= color <= 1.0
    """
    return b"%f %f %f setrgbcolor" % ( float(r), float(g), float(b), )

def cmyk(c, m, y, k):
    """
    Each color is a float 0 <= color <= 1.0
    """
    return b"%f %f %f %f setcmykcolor" % ( float(c), float(m),
                                            float(y), float(k), )

def grey(g):
    """
    Each color is a float 0 <= color <= 1.0
    """
    return b"%f setgray" % float(g)

gray = grey

def web_color(color):
    """
    Take a web-compatible hexadecimal tuple as a string and return a
    PostScript command appropriate to set that color.
    """
    # Make sure we have a legal color string
    color = color.lower().strip()

    std_colors = { "white": "ffffff",
                   "black": "000000",
                   "red": "ff0000",
                   "green": "00ff00",
                   "blue": "0000ff" }

    if color in std_colors:
        color = std_colors[color]

    if color[0] == "#": color = color[1:]
    if len(color) > 6: color = color[:5]
    if len(color) != 6: color += "0" * (6 - len(color))

    red = int(color[:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[-2:], 16)

    return rgb( red / 255.0, green / 255.0, blue / 255.0, )

class Color:
    def __bytes__(self):
        return b""

class RGBColor(Color):
    def __init__(self, r, g, b):
        """
        Each color is a float 0 <= color <= 1.0
        """
        self.r = r
        self.g = g
        self.b = b

    def __bytes__(self):
        return rgb(self.r, self.g, self.b)

class CMYKColor(Color):
    def __init__(self, c, m, y, k):
        """
        Each color is a float 0 <= color <= 1.0
        """
        self.c = c
        self.m = m
        self.y = y
        self.k = k

    def __bytes__(self):
        return cmyk(self.c, self.m, self.y, self.k)

class GreyColor(Color):
    def __init__(self, g):
        """
        Each color is a float 0 <= color <= 1.0
        """
        self.g = g

    def __bytes__(self):
        return grey(self.g)

class WebColor(Color):
    def __init__(self, color_representation):
        self.color = color_representation

    def __bytes__(self):
        return web_color(self.color)


white = GreyColor(1.0)
black = GreyColor(0.0)

red = RGBColor(1, 0, 0)
green = RGBColor(0, 1, 0)
blue = RGBColor(0, 0, 1)

class TransparentColor(Color):
    def __bytes__(self):
        return b""

    def __nonzero__(self):
        return False

transparent = TransparentColor()

######################################################################
# When I grow up, I’ll be a unit test!

if __name__ == "__main__":
    from io import BytesIO
    from .base import PSBuffer

    b = PSBuffer()

    for a in ("white", "black", "red", "green", "blue"):
        b.print(globals().get(a), f"% {a}")

    b.print()
    b.print(WebColor("#FFBE33"), b'% WebColor("#FFBE33"))')

    fp = BytesIO()
    b.write_to(fp)

    print(fp.getvalue().decode("ascii"))
