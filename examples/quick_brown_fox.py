#!/usr/bin/python

##  This file is part of psg, PostScript Generator.
##
##  Copyright 2023 by Diedrich Vorberg <diedrich@tux4web.de>
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

"""
Print a test string in a specified font.
"""

import sys, argparse, pathlib

from psbuffer.dsc import EPSDocument, Page
from psbuffer.boxes import Canvas
from psbuffer.measure import mm
from psbuffer.fonts import Type1

"""\
Create a (Encapsulated) Postscript document with one A4 page
that displays a sample of the font.
"""

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--outfile", help="Output file. "
                        "Deafults to stdout.", type=argparse.FileType("bw"),
                        default=sys.stdout.buffer)
    parser.add_argument("-s", "--font-size", help="Font size in pt",
                        type=float, default=12)
    parser.add_argument("-t", "--text",
                        default="The quick brown fox jumps over the lazy dog.",
                        help="Text to render")
    parser.add_argument("outline", help="PFA or PFB file", type=pathlib.Path)
    parser.add_argument("metrics", help="AFM file", type=pathlib.Path)

    args = parser.parse_args()

    page_margin = mm(16)
    line_height = args.font_size * 1.25

    # Load the font
    font = Type1(args.outline.open(), args.metrics.open())

    # Create the EPS document
    document = EPSDocument("a5")
    page = document.page
    canvas = page.append(Canvas(page_margin, page_margin,
                                page.w - 2*page_margin,
                                page.h - 2*page_margin))

    # Register the font with the document
    font_wrapper = page.make_font_wrapper(font, args.font_size)

    def _line_y():
        y = canvas.h
        while y >= 0.0:
            y -= line_height
            yield y
    line_y = _line_y()

    def newline():
        canvas.print(0, next(line_y), "moveto")

    canvas.print(font_wrapper.setfont())

    newline()
    canvas.print(font_wrapper.show(args.text))

    newline()
    canvas.print(font_wrapper.xshow(args.text))

    document.write_to(args.outfile)

main()
