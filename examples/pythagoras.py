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
Typeset Euclid’s proof of the famous theorem ascribed to Pythagoras
into a right triangle.
"""

import sys, os, os.path as op, argparse, pathlib, unicodedata, warnings

from hyphen import Hyphenator

from psbuffer.measure import mm
from psbuffer import utils
from psbuffer.base import ps_literal
from psbuffer.boxes import TextBox, TextBoxesExhausted
from psbuffer.dsc import EPSDocument
from psbuffer.typography.plaintext import Text

phi = 1.6181

ooo_hyphenator = Hyphenator("el_GR").syllables

def hyphenate(word):
    """
    Hyphenate `word` and return a list of syllables or None if `word` cannot
    be hyphenated.
    """
    # The ooo hyphenator works on monotonic modern Greek. Well, can’t blame
    # it: This is what Greeks write nowerdays. Our source material, however,
    # is polytonic ancient Greek and for the purpose of art I’d like to keep
    # it that way. The hyphenation will be an appropriation, but good enough
    # for me.
    # Welcome to the real world, where shits get complicated fast.
    monotonic = ''.join(c for c in unicodedata.normalize("NFD", word)
                        if unicodedata.category(c) != "Mn")
    monotonic_syllables = ooo_hyphenator(monotonic)

    if monotonic_syllables is None:
        return None
    else:
        # Make sure every letter and its modifiers are represented by one
        # codepoint.
        word = unicodedata.normalize("NFC", word)

        syllables = []
        for s in monotonic_syllables:
            l = len(s)
            syllables.append(word[:l])
            word = word[l:]

        return syllables


class TriangularTextBox(TextBox):
    def __init__(self, maxw, maxh, topwidth, slant_factor=1.0):
        """
        My triangle will always sit at 0,0 and be ready to be moved
        after the text has been rendered. We need `maxw` and `maxh`
        tp get started.
        `topwidth` is the width of the first syllable with a - on it
           (if needed)
        `slant_factor` will determin how much longer the bottom side is
           than the right one. 1.0 will result in an equal sided triangle.
        """
        super().__init__(0, 0, maxw, maxh)
        self.maxw = maxw
        self.topwidth = topwidth
        self.slant_factor = slant_factor

    def _calculate_width_at(self, y, height):
        """
        This is going to create a right triangle that’s
        """
        self._w = max(self.topwidth, (self.h-y)*self.slant_factor)
        return self._w

def main():
    parser = utils.make_example_argument_parser(
        __file__, __doc__, i=True, o=True, s=True, font=True)
    args = parser.parse_args()
    cmusr12 = utils.make_font_instance_from_args(args)

    page_margin = mm(16)
    with args.input.open("r") as fp:
        intext = fp.read()
        paras = intext.split("\n\n")

        theorem = paras[0]
        source = paras[1]

    text = Text.from_text(theorem, cmusr12, align="block",
                          hyphenate_f=hyphenate)

    # Let’s make us a cursor.
    cursor = text.make_cursor()
    # Hyphenate the first word.
    cursor.hyphenate_current()
    # Get the first syllable (maybe with a hyphen on it).
    topwidth = cursor.current.hyphened_width

    # Create the EPS document
    document = EPSDocument("a4 landscape")
    page = document.page

    tb = page.append(TriangularTextBox(page.w, page.h, topwidth, 1.396))
    # Where does 1.396 come from? Try and error.
    # What? This is art!

    try:
        text.typeset([tb,])
    except TextBoxesExhausted:
        warnings.warn("Couldn’t fit the theorem into the triangle.")


    # Typeset source. Man, helper functions are needed.
    cmusr10 = cmusr12.font.make_instance(
        args.font_size*0.5, line_height=args.font_size)
    tb.tail.print(0.25, "setgray")
    source_tb = tb.tail.append(TextBox(0, tb.room_left - cmusr10.line_height,
                                       tb.w, cmusr10.line_height))
    source_text = Text.from_text(source, cmusr10, align="left")
    source_text.typeset([source_tb])

    # Place the textbox horizontylly centered and top and bottom margin
    # to have golden ratio.
    tb.head.print("% Move triangle")
    left = (page.w - tb.w)/2
    top = tb.room_left * (1-1/phi)
    tb.head.print(left, -top, "translate")

    document.write_to(args.outfile.open("wb"))

main()
