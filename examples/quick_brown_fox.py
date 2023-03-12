#!/usr/bin/env python

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

from psbuffer import utils
from psbuffer.dsc import EPSDocument, Page
from psbuffer.boxes import Canvas
from psbuffer.measure import mm

"""
Create a (Encapsulated) Postscript document with one A4 page
that displays a sample of the font.
"""

def main():
    parser = utils.make_example_argument_parser(
        __file__, __doc__, o=True, s=True, font=True)
    parser.add_argument("-t", "--text",
                        default="The quick brown fox jumps over the lazy dog.",
                        help="Text to render")

    args = parser.parse_args()

    font = utils.make_font_instance_from_args(args)

    page_margin = mm(16)
    line_height = args.font_size * 1.25

    # Create the EPS document
    document = EPSDocument("a5")
    page = document.page
    canvas = page.append(Canvas(page_margin, page_margin,
                                page.w - 2*page_margin,
                                page.h - 2*page_margin))

    # Register the font with the document
    def _line_y():
        y = canvas.h
        while y >= 0.0:
            y -= line_height
            yield y
    line_y = _line_y()

    def newline():
        canvas.print(0, next(line_y), "moveto")

    font.setfont(canvas)

    newline()
    canvas, font.show(canvas, [ord(c) for c in args.text])

    newline()
    font.xshow(canvas, [ord(c) for c in args.text])

    document.write_to(args.outfile)

main()
