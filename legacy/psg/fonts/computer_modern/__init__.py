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
the classic and beautiful Computer Modern fonts in this directory.
"""

import os.path as op
from t4.psg.fonts.font import font
from t4.psg.fonts.type1 import lazy_loader as lazy_loader_base

class lazy_loader(lazy_loader_base):
    def here(self):
        return op.abspath(op.dirname(__file__))

bright_bold = cmunbbx = lazy_loader("cmunbbx") # CMUBright-Bold
bright_boldoblique = cmunbxo = lazy_loader("cmunbxo") # CMUBright-BoldOblique
bright_oblique = cmunbmo = lazy_loader("cmunbmo") # CMUBright-Oblique
bright_roman = cmunbmr = lazy_loader("cmunbmr") # CMUBright-Roman
bright_semibold = cmunbsr = lazy_loader("cmunbsr") # CMUBright-Semibold
bright_semiboldoblique = cmunbso = lazy_loader("cmunbso") # CMUBright-SemiboldOblique
classicalserif_italic = cmunci = lazy_loader("cmunci") # CMUClassicalSerif-Italic
concrete_bold = cmunobx = lazy_loader("cmunobx") # CMUConcrete-Bold
concrete_bolditalic = cmunobi = lazy_loader("cmunobi") # CMUConcrete-BoldItalic
concrete_italic = cmunoti = lazy_loader("cmunoti") # CMUConcrete-Italic
concrete_roman = cmunorm = lazy_loader("cmunorm") # CMUConcrete-Roman
sansserif = cmunss = lazy_loader("cmunss") # CMUSansSerif
sansserif_bold = cmunsx = lazy_loader("cmunsx") # CMUSansSerif-Bold
sansserif_boldoblique = cmunso = lazy_loader("cmunso") # CMUSansSerif-BoldOblique
sansserif_demicondensed = cmunssdc = lazy_loader("cmunssdc") # CMUSansSerif-DemiCondensed
sansserif_oblique = cmunsi = lazy_loader("cmunsi") # CMUSansSerif-Oblique
serif_bold = cmunbx = lazy_loader("cmunbx") # CMUSerif-Bold
serif_bolditalic = cmunbi = lazy_loader("cmunbi") # CMUSerif-BoldItalic
serif_boldnonextended = cmunrb = lazy_loader("cmunrb") # CMUSerif-BoldNonextended
serif_boldslanted = cmunbl = lazy_loader("cmunbl") # CMUSerif-BoldSlanted
serif_italic = cmunti = lazy_loader("cmunti") # CMUSerif-Italic
serif_roman = cmunrm = lazy_loader("cmunrm") # CMUSerif-Roman
serif_romanslanted = cmunsl = lazy_loader("cmunsl") # CMUSerif-RomanSlanted
serif_uprightitalic = cmunui = lazy_loader("cmunui") # CMUSerif-UprightItalic
typewriter_bold = cmuntb = lazy_loader("cmuntb") # CMUTypewriter-Bold
typewriter_bolditalic = cmuntx = lazy_loader("cmuntx") # CMUTypewriter-BoldItalic
typewriter_italic = cmunit = lazy_loader("cmunit") # CMUTypewriter-Italic
typewriter_light = cmunbtl = lazy_loader("cmunbtl") # CMUTypewriter-Light
typewriter_lightoblique = cmunbto = lazy_loader("cmunbto") # CMUTypewriter-LightOblique
typewriter_oblique = cmunst = lazy_loader("cmunst") # CMUTypewriter-Oblique
typewriter_regular = cmuntt = lazy_loader("cmuntt") # CMUTypewriter-Regular
typewritervariable = cmunvt = lazy_loader("cmunvt") # CMUTypewriterVariable
typewritervariable_italic = cmunvi = lazy_loader("cmunvi") # CMUTypewriterVariable-Italic
