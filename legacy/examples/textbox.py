#!/usr/bin/python
# -*- coding: utf-8 -*-

##  This file is part of psg, PostScript Generator.
##
##  Copyright 2006 by Diedrich Vorberg <diedrich@tux4web.de>
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
This program uses psg.drawing.textbox to typeset text.
"""

import sys, unicodedata

from t4.psg.document.dsc import dsc_document
from t4.psg.util import *
from t4.psg.drawing.box import box, textbox
from t4.psg.fonts.type1 import type1
from t4.psg.fonts import computer_modern as cmu

two_paragraphs = u"""\
1 Im Anfang war das Wort, und das Wort war bei Gott, und Gott war das Wort. 2 Dasselbe war im Anfang bei Gott. 3 Alle Dinge sind durch dasselbe gemacht, und ohne dasselbe ist nichts gemacht, was gemacht ist.  4 In ihm war das Leben, und das Leben war das Licht der Menschen.  5 Und das Licht scheint in der Finsternis, und die Finsternis hat's nicht ergriffen. (…)
14 Und das Wort ward Fleisch und wohnte unter uns, und wir sahen seine Herrlichkeit, eine Herrlichkeit als des eingeborenen Sohnes vom Vater, voller Gnade und Wahrheit.
üäöÜÄÖß
"""

two_paragraphs_greek = u"""\
1 Ἐν ἀρχῇ ἦν ὁ λόγος, καὶ ὁ λόγος ἦν πρὸς τὸν θεόν, καὶ θεὸς ἦν ὁ λόγος.(…)
14 Καὶ ὁ λόγος σὰρξ ἐγένετο καὶ ἐσκήνωσεν ἐν ἡμῖν, καὶ ἐθεασάμεθα τὴν δόξαν αὐτοῦ, δόξαν ὡς μονογενοῦς παρὰ πατρός, πλήρης χάριτος καὶ ἀληθείας.
Composed: Ἀ Ἐ Ὀ Ὠ
Types deparately: ᾿Α ᾿Ε ᾿Ο ᾿Ω
Ἐν"""

special_characters = u"""\
üäöÜÄÖß € „Anführungszeichen“
Was ist denn noch so wichtig... 
¡ “ ¶ ¢ [ ] | { }  ≠ ¿ « ∑  € ® † Ω ¨ ⁄ ø π •  æ œ @  ∆ º ª  © ƒ ∂ ‚ å ¥ ≈ ç √ ∫ ~ µ ∞ … – ¬ ” # £ ﬁ ^ \ ˜ · ¯ ˙ » „ ‰ ¸ ˝ ˇ Á Û  Ø ∏ °  Å Í ™ Ï Ì Ó ı ˆ ﬂ Œ Æ ’ ’ ‡ Ù Ç  ◊ ‹ › ˘ ˛ ÷ — 
Der Unicode-Support läßt nicht viel zu wünschen über, oder? 
"""

def box0(box, he, **kw):
    box.set_font(he, font_size=9, paragraph_spacing=18)
    box.typeset(two_paragraphs)

def box1(box, he, **kw):
    box.set_font(he, font_size=9, paragraph_spacing=18,
                     alignment="justify", kerning=True)
    box.typeset(two_paragraphs)

def box2(box, tr, **kw):
    box.set_font(tr, font_size=9, paragraph_spacing=18,
                     alignment="right", kerning=True)
    box.typeset(two_paragraphs)

def box3(box, tr, **kw):
    box.set_font(tr, font_size=9, paragraph_spacing=18,
                     alignment="center", kerning=True)
    box.typeset(two_paragraphs)

def box4(box, tr, he, **kw):
    box.set_font(he, font_size=9, paragraph_spacing=18,
                 line_spacing=3, alignment="left", kerning=True)
    box.typeset(two_paragraphs_greek)

def box5(box, tr, **kw):
    box.set_font(tr, font_size=9, paragraph_spacing=18,
                 line_spacing=4, alignment="left", kerning=True)
    box.typeset(special_characters)

def box6(box, ba, **kw):
    box.set_font(ba, font_size=9, paragraph_spacing=18,
                     alignment="left", kerning=True)
    box.typeset(two_paragraphs)

def box7(box, he, **kw):
    box.set_font(he, font_size=10, paragraph_spacing=18,
                 line_spacing=2, alignment="left", kerning=True)
    box.typeset(two_paragraphs)

def main(argv):
    document = dsc_document("My first textbox example and testbed")
    page = document.page()
    canvas = page.canvas(margin=mm(18), border=False)

    tr = cmu.serif_roman()
    tr = page.register_font(tr)

    he = cmu.sansserif()
    he = page.register_font(he)

    al = type1("Kerkis.pfa", "Kerkis.afm")
    al = page.register_font(al)

    ba = type1("BlackadderITC-Regular.pfa", "BlackadderITC-Regular.afm")
    ba = page.register_font(ba)
    
    for counter, bb in enumerate(eight_squares(canvas)):        
        func = globals().get("box%i" % counter, None)
        
        if func is None:
            break
        else:
            box = textbox.from_bounding_box(canvas, bb, border=True)
            canvas.append(box)
            func(**locals())

    fp = open(sys.argv[0] + ".ps", "w")
    document.write_to(fp)
    fp.close()
        
main(sys.argv)


