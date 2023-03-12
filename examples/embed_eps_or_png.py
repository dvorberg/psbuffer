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

import argparse, pathlib
from io import BytesIO

from PIL import Image

from psbuffer import utils
from psbuffer.measure import mm
from psbuffer.dsc import Document, Page
from psbuffer.boxes import Canvas, EPSImage, RasterImage

def main():
    parser = utils.make_example_argument_parser(
        __file__, __doc__, o=True, s=True)
    args = parser.parse_args()
    parser.add_argument("imgpath", type=pathlib.Path)
    args = parser.parse_args()

    document = Document()
    page = document.append(Page(size=args.papersize))
    canvas = page.append(Canvas(mm(18), mm(18), page.w-mm(36), page.h-mm(36)))

    if args.imgpath.suffix == ".eps":
        img = EPSImage(args.imgpath.open("rb"),
                       document_level=False, border=True,
                       comment=args.imgpath.name)
    else:
        img = RasterImage(Image.open(args.imgpath.open("rb")),
                          border=True, comment=args.imgpath.name)
    img.fit(canvas)

    fp = BytesIO()
    document.write_to(fp)

main()
