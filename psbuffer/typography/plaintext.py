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

import functools, copy, itertools, re
from typing import Sequence

from ..boxes import Canvas
from ..fonts.fontbase import FontInstance
from ..fonts.encoding_tables import breaking_whitespace_chars

"""
Classes to represent text formatted with a single FontSpec (font, size,
kerning, char_spacing) throughout.
"""

class Syllable(object):
    def __init__(self, font_wrapper:FontInstance, codepoints:Sequence[int],
                 final=False, space_width=None):
        self.font = font_wrapper
        self.codepoints = codepoints
        self.final = final
        self._space_width = space_width

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
            return Syllable(self. font, self.codepoints + [ 45, ])

    @property
    def height(self):
        return self.font.size

    @property
    def space_width(self):
        if self.final:
            return self._space_width
        else:
            return 0.0

    def xshow(self, container):
        return self.font.xshow(container, self.codepoints)

    def __str__(self):
        return "".join([chr(cp) for cp in self.codepoints])

    def __repr__(self):
        return f"-{self}@{self.width:.2f}pt F={self.final}-"


class Word(Syllable):
    def __init__(self, font_wrapper:FontInstance,
                 word:str, whitespace_codepoint=32, hyphenate_f=None):
        super().__init__(font_wrapper, [ ord(char) for char in word ],
                         True, font_wrapper.charwidth(whitespace_codepoint))
        self.word = word
        self.whitespace_codepoint = whitespace_codepoint

        if hyphenate_f:
            self._hyphenate = hyphenate_f
        else:
            self._hyphenate = lambda characters: [ characters, ]

    def __str__(self):
        return self.word

    characters_re = re.compile(r"(\w+)(.*)")
    def hyphenate(self, word):
        # This is much more complicated than one would think.
        # The hyphenator only knows about regular language words.
        # That’s what we feed him. We keep the rest of the characters
        # and put them back in the result on returning it.
        match = self.characters_re.match(word)
        if match is None:
            # Can’t do anything. Return input as-is.
            return [ word, ]
        else:
            start, extra = match.groups()

        ret = self._hyphenate(start)
        if ret:
            if extra:
                # Put the extra characters on the last syllable.
                ret[-1] += extra

            return ret
        else:
            # No result from the hyphenator: Return input as is.
            return [ word, ]

    def withHyphen(self):
        return self

    @property
    def syllables(self):
        ret = [ Syllable(self.font, [ ord(s) for s in chars ],
                         space_width=self.space_width)
                for chars in self.hyphenate(self.word) ]
        ret[-1].final = True
        return ret

    def __repr__(self):
        return f"“{self.word}@{self.width:.2f}pt”"

breaking_whitespace_re = re.compile(r"([%s]+)" % breaking_whitespace_chars)
class SoftParagraph(object):
    def __init__(self, words:Sequence[Word], line_height:float=None):
        self.words = list(words)
        self.line_height = line_height

    def make_line_iterator(self, maxwidth):
        return LineIterator(self.words, maxwidth)

    @classmethod
    def from_text(cls, text:str, line_height:float=None):
        result = breaking_whitespace_re.split(text)

        def words(result):
            it = iter(result)
            while (pair := tuple(itertools.islice(it, 2))):
                if len(pair) == 1:
                    word, = pair
                    whitespace_codepoint = 32
                else:
                    word, whitespace = pair
                    whitespace_codepoint = ord(whitespace[0])

                yield Word(cmusr12, word, whitespace_codepoint, hyphenator)

        return cls(words(result), line_height)


class WordIterator(object):
    def __init__(self, words:Sequence[Syllable]):
        self.words = words
        self.syllables = []

    def push_line(self, line):
        self.syllables = list(line) + self.syllables

    def push_syllables(self, syllables):
        self.syllables.extend(syllables)

    def __iter__(self):
        for word in self.words:
            while self.syllables:
                yield self.syllables[0]
                del self.syllables[0]

            yield word

        while self.syllables:
            yield self.syllables[0]
            del self.syllables[0]


class Line(list):
    """
    A line is a list of Words/Syllables. It has a `width`, which is the sum
    of the widths of its words plus the sum of the width of white-space in
    between those words.
    """
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

    @property
    def last_space_width(self):
        if len(self) > 0:
            return self[-1].space_width
        else:
            return 0.0

    def withHyphen(self):
        ret = Line()

        if len(self) > 0:
            for a in self[:-1]:
                ret.append(a)
            ret.append(self[-1].withHyphen())

        return ret

    @property
    def height(self) -> float:
        return max([ e.height for e in self ])


class LineIterator(object):
    def __init__(self, words:WordIterator, initial_maxwidth:float=None):
        self._maxwidth = initial_maxwidth
        self.words = WordIterator(words)

        self._done = False

    @property
    def maxwidth(self):
        return self._maxwidth

    @maxwidth.setter
    def maxwidth(self, maxwidth:float):
        self._maxwidth = maxwidth

    def __iter__(self):
        line = Line()

        for element in self.words:
            # A syllable that doesn’t fit a line by itself.
            if not hasattr(element, "syllables") and \
               element.hyphenedWidth > self._maxwidth:
                # If there is a line with something on it, yield it.
                if line:
                    yield line
                    # Reset the line
                    line = Line()

                # Yield the over-sized syllable on a line by itself.
                yield Line(element)

            lwidth = line.width + line.last_space_width + element.hyphenedWidth
            if lwidth > self._maxwidth:
                if hasattr(element, "syllables"):
                    # Hyphenate
                    self.words.push_syllables(element.syllables)
                    continue
                else:
                    # newline!
                    yield line
                    line = Line(element)
            else:
                line.append(element)

        if line:
            yield line

        self._done = True

    def push_line(self, line:Line):
        """
        Hand back a line to the iterator.
        """
        self.words.push_line(line)

    @property
    def done(self) -> bool:
        """
        Returns True, if all lines have been yielded.
        """
        return self._done

newline_re = re.compile("(?:\r\n|\r|\n)+")
class HardParagraph(object):
    def __init__(self, soft_paragraphs:Sequence[SoftParagraph],
                 margin_top:float=0.0, margin_bottom:float=0.0,
                 align="left"):
        self.soft_paragraphs = soft_paragraphs
        self.margin_top = margin_top
        self.margin_bottom = margin_bottom

        assert align in { "left", "right", "center", }
        self.align = align

    @classmethod
    def from_text(cls, text,
                  line_height:float=None,
                  margin_top:float=0.0,
                  margin_bottom:float=0.0,
                  align="left"):
        return cls([SoftParagraph.from_text(part, line_height)
                    for part in newline_re.split(text)],
                   margin_top, margin_bottom, align)

class ParagraphIterator(object):
    def __init__(self, paragraphs:Sequence[HardParagraph]):
        self.paragraphs = paragraphs


def typeset(paragraphs:ParagraphIterator, canvases:Sequence[Canvas]):
    pass


def main():
    import sys, argparse, pathlib

    from hyphen import Hyphenator

    from psbuffer.dsc import EPSDocument, Page
    from psbuffer.measure import mm
    from psbuffer.fonts import Type1

    from ..utils import splitfields

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--outfile", help="Output file. "
                        "Deafults to stdout.", type=argparse.FileType("bw"),
                        default=None)
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
    textbox_a = page.append(Canvas(page_margin, page_margin,
                                   mm(50), page.h - 2*page_margin,
                                   border=True))
    textbox_b = page.append(Canvas(page_margin + mm(70), page_margin,
                                   mm(50), page.h - 2*page_margin,
                                   border=True))

    cmusr12 = cmusr.make_instance(args.font_size)

    genesis = ("In the beginning God created the heaven and the earth. "
               "And the earth was without form, and void; and darkness "
               "was upon the face of the deep. And the Spirit of God moved "
               "upon the face of the waters. And God said, Let there be "
               "light: and there was light. And God saw the light, that "
               "it was good: and God divided the light from the darkness. "
               "And God called the light Day, and the darkness he called "
               "Night. And the evening and the morning were the first day. ")

    tests = ( "Well that’s Supercalifragilisticexpialidocious! "
              "Whatever happens on this line: Don’t Break Me! "
              "And make sure I am not\u202Fbroken\u202Feither. "
              "But\u2000I\u2001am\u2002flexible\u2003and\u2004may\u2005be"
              "\u2006broken!")

    genesis_de = ("Am Anfang schuf Gott Himmel und Erde. Und die Erde war  "
                  "wüst und leer, und es war finster auf der Tiefe; und der "
                  "Geist Gottes schwebte auf dem Wasser. Und Gott sprach: Es "
                  "werde Licht! Und es ward Licht. Und Gott sah, daß das "
                  "Licht gut war. Da schied Gott das Licht von der Finsternis "
                  "und nannte das Licht Tag und die Finsternis Nacht. Da ward "
                  "aus Abend und Morgen der erste Tag.")

    # Whatever happens:
    a = ("Don’t Break Me! "
         "And make very, very sure of it.")
    # Whatever happens:
    b = ("Don’t Break Me! "
         "And make very, very sure of it.")


    def print_debug(lines:LineIterator):
        for no, line in enumerate(lines):
            for element in line[:-1]:
                print(element, end=" " if element.space_width > 0.0 else "")

            if no == 5:
                lines.maxwidth = lines.maxwidth / 2.0
            elif no == 10:
                lines.maxwidth = lines.maxwidth * 2.0

            print(line[-1].withHyphen())

    paragraphs = [ HardParagraph.from_text(genesis),
                   HardParagraph.from_text(tests), ]



    #typeset(genesis, textbox_a)
    #print("*"*60)
    #typeset(b, textbox_b)


    document.write_to(args.outfile)

if __name__ == "__main__":
    main()
