#!/usr/bin/python

##  This file is part of psbuffer.
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

import functools, copy
from typing import Sequence
from ..fonts.fontbase import FontWrapper

"""
Classes to represent text formatted with a single FontWrapper (font, size,
kerning, char_spacing) throughout.
"""

class Syllable(object):
    def __init__(self, font_wrapper:FontWrapper, codepoints:Sequence[int],
                 final=False):
        self.font = font_wrapper
        self.codepoints = codepoints
        self.final = final

    @functools.cached_property
    def width(self):
        return self.font.charswidth(self.codepoints)

    @functools.cached_property
    def hyphenedWidth(self):
        if self.final:
            return self.width
        else:
            return self.width + self.font.charwidth(45) # 45 = “-”

    def withHyphen(self):
        if self.final:
            return self
        else:
            return Syllable(self. font, self.codepoints + [ 45, ], False)

    def height(self):
        return self.font.size

    @property
    def space_width(self):
        if self.final:
            return self.font.charwidth(32)
        else:
            return 0.0

    def __str__(self):
        return "".join([chr(cp) for cp in self.codepoints])

    def __repr__(self):
        return f"-{self}@{self.width:.2f}pt F={self.final}-"


class Word(Syllable):
    def __init__(self, font_wrapper:FontWrapper,
                 word:str, hyphenate_f=None):
        super().__init__(font_wrapper, [ ord(char) for char in word ])
        self.word = word

        if hyphenate_f:
            self._hyphenate = hyphenate_f
        else:
            self._hyphenate = lambda characters: [ characters, ]

    def __str__(self):
        return self.word

    def hyphenate(self, word):
        ret = self._hyphenate(word)
        if ret:
            return ret
        else:
            return [ word, ]

    def withHyphen(self):
        return self

    @property
    def syllables(self):
        ret = [ Syllable(self.font, [ ord(s) for s in chars ])
                for chars in self.hyphenate(self.word) ]
        ret[-1].final = True
        return ret

    @property
    def space_width(self):
        return self.font.charwidth(32) # The width of a space char in our font.

    def __repr__(self):
        return f"“{self.word}@{self.width:.2f}pt”"

class SoftParagraph(object):
    def __init__(self, words:Sequence[Word]):
        self.words = words
        self.line_height = line_height

    def lines(self, width:float):
        """
        Yield lines (lists of Word or Syllable objects) of which each
        either
           - Has a combined width <= `width`
           - or consists of a single Syllable width width > `width`.
        """
        syllables = []
        def elements():
            for word in self.words:
                while syllables:
                    yield syllables[0]
                    del syllables[0]

                yield word

        class Line(list):
            def __init__(self, *args):
                super().__init__()

                self.width = 0.0

                for a in args:
                    self.append(a)

            def append(self, element):
                self.width += element.width
                if len(self) > 0:
                    self.width += self[-1].space_width
                super().append(element)

            def __iter__(self):
                if len(self) > 0:
                    for item in self[:-1]:
                        yield item

                    yield self[-1].withHyphen()

        line = Line()
        for element in elements():
            # A syllable that doesn’t fit a line by itself.
            if isinstance(element, Syllable) and element.hyphenedWidth > width:
                # If there is a line with something on it, yield it.
                if line:
                    yield line
                    # Reset the line
                    line = Line()

                # Yield the over-sized syllable on a line by itself.
                yield Line(element)

            if line.width + element.hyphenedWidth > width:
                if isinstance(element, Word):
                    # Hyphenate
                    syllables.extend(element.syllables)
                else:
                    # newline!
                    yield list(line)
                    line = Line(element)
            else:
                line.append(element)

        if line:
            yield line


class HardParagraph(object):
    def __init__(self, soft_paragraphs:Sequence[SoftParagraph],
                 margin_top:float=0.0, margin_bottom:float=0.0):
        self.soft_paragraphs = soft_paragraphs
        self.margin_top = margin_top
        self.margin_bottom = margin_bottom

if __name__ == "__main__":
    import sys, argparse, pathlib

    from hyphen import Hyphenator

    from psbuffer.dsc import EPSDocument, Page
    from psbuffer.boxes import Canvas
    from psbuffer.measure import mm
    from psbuffer.fonts import Type1

    from ..utils import splitfields

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--outfile", help="Output file. "
                        "Deafults to stdout.", type=argparse.FileType("bw"),
                        default=sys.stdout.buffer)
    parser.add_argument("-s", "--font-size", help="Font size in pt",
                        type=float, default=12)
    #parser.add_argument("-t", "--text",
    #                    default="The quick brown fox jumps over the lazy dog.",
    #                    help="Text to render")

    parser.add_argument("outline", help="PFA or PFB file", type=pathlib.Path)
    parser.add_argument("metrics", help="AFM file", type=pathlib.Path)

    args = parser.parse_args()

    # Download and install the hyphenation dict for German, if needed
    hyphenator = Hyphenator("en_US").syllables
    # de_DE `language`defaults to 'en_US'

    page_margin = mm(16)
    line_height = args.font_size * 1.25

    # Load the font
    cmusr = Type1(args.outline.open(), args.metrics.open())

    # Create the EPS document
    document = EPSDocument("a5")
    page = document.page
    canvas = page.append(Canvas(page_margin, page_margin,
                                page.w - 2*page_margin,
                                page.h - 2*page_margin))

    # Register the font with the document
    cmusr12 = page.make_font_wrapper(cmusr, args.font_size)

    genesis = ("In the beginning God created the heaven and the earth. "
               "And the earth was without form, and void; and darkness "
               "was upon the face of the deep. And the Spirit of God moved "
               "upon the face of the waters. And God said, Let there be "
               "light: and there was light. And God saw the light, that "
               "it was good: and God divided the light from the darkness. "
               "And God called the light Day, and the darkness he called "
               "Night. And the evening and the morning were the first day. "
               "Well that’s Supercalifragilisticexpialidocious!")

    genesis_de = ("Am Anfang schuf Gott Himmel und Erde. Und die Erde war  "
                  "wüst und leer, und es war finster auf der Tiefe; und der "
                  "Geist Gottes schwebte auf dem Wasser. Und Gott sprach: Es "
                  "werde Licht! Und es ward Licht. Und Gott sah, daß das "
                  "Licht gut war. Da schied Gott das Licht von der Finsternis "
                  "und nannte das Licht Tag und die Finsternis Nacht. Da ward "
                  "aus Abend und Morgen der erste Tag.")

    words = [ Word(cmusr12, word, hyphenator, )
              for word in splitfields(genesis) ]
    sp = SoftParagraph(words)

    for line in sp.lines(mm(50)):
        line = list(line)
        for element in line[:-1]:

            print(element, end=" " if element.space_width > 0.0 else "")
        print(line[-1])
