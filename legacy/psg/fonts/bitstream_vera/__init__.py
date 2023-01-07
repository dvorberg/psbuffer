#!/usr/bin/python
# -*- coding: utf-8 -*-

##  This file is part of psg, PostScript Generator.
##
##  Copyright 2014 by Diedrich Vorberg <diedrich@tux4web.de>
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

"""\
This module (lazily) provides t4.psg.fonts.type1.type1 objects for each of
the popular Bitstream Vera typefaces contained in this directory.
"""

import os.path as op
from t4.psg.fonts.font import font
from t4.psg.fonts.type1 import type1
from t4.psg.fonts.type1 import lazy_loader as lazy_loader_base

class lazy_loader(lazy_loader_base):
    def here(self):
        return op.abspath(op.dirname(__file__))

sans_roman = lazy_loader("BitstreamVeraSans-Roman") # Sans-Roman
sans_oblique = lazy_loader("BitstreamVeraSans-Oblique") # Sans-Oblique
sans_bold = lazy_loader("BitstreamVeraSans-Bold") # Sans-Bold
sans_boldoblique = lazy_loader("BitstreamVeraSans-BoldOblique") # Sans-BoldOblique

serif_roman = lazy_loader("BitstreamVeraSerif-Roman") # Serif-Roman
serif_bold = lazy_loader("BitstreamVeraSerif-Bold") # Serif-Bold

sansmono_roman = lazy_loader("BitstreamVeraSansMono-Roman") # SansMono-Roman
sansmono_oblique = lazy_loader("BitstreamVeraSansMono-Oblique") # SansMono-Oblique
sansmono_bold = lazy_loader("BitstreamVeraSansMono-Bold") # SansMono-Bold
sansmono_boldoblique = lazy_loader("BitstreamVeraSansMono-BoldOb") # SansMono-BoldOb

