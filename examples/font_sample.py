#!/usr/bin/python

##  This file is part of psg, PostScript Generator.
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

"""
This program creates a table containing a set of glyphs from the font
provided on the command line (as pfb/afm file pair) and create a
PostScript document on stdout.
"""

import sys, argparse, pathlib, unicodedata

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
    parser.add_argument("outline", help="PFA or PFB file", type=pathlib.Path)
    parser.add_argument("metrics", help="AFM file", type=pathlib.Path)

    args = parser.parse_args()

    cellpadding = mm(1)
    page_margin = mm(16)

    font_size = args.font_size
    chars = """ABCDEFGHIJKLMNOPQRSTUVWXYZ
               abcdefghijklmnopqrstuvwxyz
               äöüÄÖÜß 0123456789
               !\"§$%&/()=?€@ „“ “” »«
               «∑€®†Ωπ@∆ºª©ƒ∂‚å¥≈√∫∞"""

    # Load the font
    font = Type1(args.outline.open(), args.metrics.open())

    # Create the EPS document
    document = EPSDocument("a4")
    page = document.page

    # Register the font with the document
    font_wrapper = page.make_font_wrapper(font, font_size)

    # Ok, we got to find out a number of things: Dimensions of the cells,
    # dimensions of the table
    m = 0
    for char in chars:
        m = max(m, font.metrics.charwidth(ord(char), font_size))

    td_width = m + 2*cellpadding
    td_height = font_size + 2*cellpadding

    lines = [ line.strip() for line in chars.split("\n") ]
    lines.reverse()

    m = 0
    for line in lines:
        m = max(m, len(line))

    cols = m
    rows = len(lines)

    table_width = cols * td_width
    table_height = rows * td_height

    # Create a canvas at the coordinates of the page_margins and width
    # the table's size.
    table = page.append(Canvas(page_margin, page_margin,
                               table_width, table_height,
                               border=True))

    # Draw the table grid by drawing row and column boundaries.
    table.print("gsave")
    table.print("0.4 setgray [] 0.5 setdash")
    for a in range(1, cols):
        table.print("newpath")
        table.print(a * td_width, 0, "moveto")
        table.print(a * td_width, table_height, "lineto")
        table.print("stroke")

    for a in range(1, rows):
        table.print("newpath")
        table.print(0, a * td_height, "moveto")
        table.print(table_width, a * td_height, "lineto")
        table.print("stroke")

    table.print("grestore")

    # This is what font_wrapper.setfont() does:
    table.print("/%s findfont" % font_wrapper.encoding.ps_name)
    table.print("%f scalefont" % font_size)
    table.print("setfont")

    # Fill the boxes.
    for lc, line in enumerate(lines):
        for cc, char in enumerate(line):
            x = cc * td_width + cellpadding
            y = lc * td_height + cellpadding
            psrep = font_wrapper.postscript_representation( [ord(char),] )

            table.print(x, y, "moveto")
            table.print(b"(%s) show" % psrep)

    page.bounding_box = table.bounding_box
    document.write_to(args.outfile)

main()
