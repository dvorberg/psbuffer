#!/usr/bin/python
# -*- coding: utf-8; -*-

##  This file is part of psg, PostScript Generator.
##
##  Copyright 2006-14 by Diedrich Vorberg <diedrich@tux4web.de>
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
psg printing the old line on a sheet of paper. The text drawing
functions are not written, yet, so I type in the PostScript directly.
"""

import sys

from t4.psg.document.dsc import dsc_document
from t4.psg.util import *

def main():

    document = dsc_document("Hello, world!")
    page = document.page()
    canvas = page.canvas(margin=mm(18))

    print >> canvas, "/Helvetica findfont"
    print >> canvas, "20 scalefont"
    print >> canvas, "setfont"
    print >> canvas, "0 0 moveto"
    print >> canvas, ps_escape("Hello, world!"), " show"

    fp = open("ps_hello_world.ps", "w")
    document.write_to(fp)
    fp.close()
    
main()
