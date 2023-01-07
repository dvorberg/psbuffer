#!/usr/bin/python
# -*- coding: utf-8; mode: python; ispell-local-dictionary: "english"; -*-

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

"""
These styles are defined around the Computer Modern font family
shipped with t4.psg and provided by the t4.psg.fonts.computer_modern
module for testing purposes.

The two module variables cmu_sans_serif and cmu_serif provide complete sets
of engine two styles that can be used to render text.
"""
from t4.psg.drawing.engine_two.styles import font_family, style
from t4.psg.fonts.computer_modern import sansserif, sansserif_bold, \
     sansserif_oblique, sansserif_boldoblique, \
     serif_roman, serif_italic, serif_bold, serif_bolditalic

from t4.psg.util import colors
from t4.psg.drawing.engine_two.styles import backgrounds, lists     

sans_serif_ff = font_family({ "regular": sansserif,
                              "italic": sansserif_oblique,
                              "bold": sansserif_bold,
                              "bold-italic": sansserif_boldoblique })

serif_ff = font_family({ "regular": serif_roman,
                         "italic": serif_italic,
                         "bold": serif_bold,
                         "bold-italic": serif_bolditalic })

sans_serif_text = style({ "font-family": sans_serif_ff,
                          "font-size": 10,
                          "font-weight": "normal",
                          "text-style": "normal",
                          "line-height": 12.5,
                          "kerning": True,
                          "char-spacing": 0,
                          "color": colors.black,
                          "hyphenator": None, },
                        name="cmuss")

serif_text = sans_serif_text + {"font-family": serif_ff}

box = style({ "margin": (0, 0, 0, 0),
              "padding": (0, 0, 0, 0),
              "background": backgrounds.none() },
            name="null box")

paragraph = style({"list-style": lists.none(),
                   "text-align": "left",},
                  name="left")


cmu_sans_serif = sans_serif_text + box + paragraph
cmu_sans_serif.set_name("cmuss")

cmu_serif = serif_text + box + paragraph
cmu_serif.set_name("cmus")

        
