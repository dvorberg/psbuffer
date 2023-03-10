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

import functools, copy, itertools, re, warnings
from typing import Sequence, Iterator

from ..measure import has_dimensions
from ..base import ps_literal
from ..boxes import TextBox, TextBoxesExhausted
from ..fonts.fontbase import FontInstance
from ..fonts.encoding_tables import breaking_whitespace_chars

from .cursors import Cursor

"""
Classes to represent text formatted with a single FontSpec (font, size,
kerning, char_spacing) throughout.
"""

def _pretty_wordlist(self_words):
    words = []
    for word in self_words:
        words.append(word)
        if word.space_width > 0:
            words.append(" ")

    if words:
        if words[-1] == " ":
            del words[-1]
        words[-1] = words[-1].with_hyphen()

        return "".join([str(w) for w in words])
    else:
        return ""

class Syllable(has_dimensions):
    def __init__(self, font_wrapper:FontInstance, codepoints:Sequence[int],
                 final=False, space_width=None):
        self.font = font_wrapper
        self.codepoints = codepoints
        self.final = final
        self._space_width = space_width

    @functools.cached_property
    def hyphened_width(self):
        if self.final:
            return self.w
        else:
            return self.w + self.hyphen_width

    @functools.cached_property
    def hyphen_width(self):
        """
        The width of the hyphen in this word’s font.
        """
        return self.font.charwidth(45) # 45 = “-”

    def with_hyphen(self):
        if self.final:
            return self
        else:
            return Syllable(self.font, self.codepoints + [ 45, ]) # 45 = “-”

    @functools.cached_property
    def w(self):
        return self.font.charswidth(self.codepoints)

    @property
    def h(self):
        return self.font.size

    @property
    def space_width(self):
        if self.final:
            return self._space_width
        else:
            return 0.0

    def xshow_params(self, container):
        return self.font.xshow_params(container, self.codepoints)

    def __str__(self):
        return "".join([chr(cp) for cp in self.codepoints])

    def __repr__(self):
        return f"-{self}@{self.w:.2f}pt F={self.final}-"

    @property
    def syllables(self):
        # Returning None indicates that this element can’t be hyphenated.
        return [ self, ]

    @property
    def monosyllabic(self):
        return True

    @property
    def is_hyphenated(self):
        return True


class Word(Syllable):
    def __init__(self, font_wrapper:FontInstance,
                 word:str, whitespace_codepoint=32, hyphenate_f=None):
        super().__init__(font_wrapper, [ ord(char) for char in word ],
                         True, font_wrapper.charwidth(whitespace_codepoint))
        self.word = word
        self._syllables = None

        self.whitespace_codepoint = whitespace_codepoint

        if hyphenate_f:
            self._hyphenate_f = hyphenate_f
        else:
            self._hyphenate_f = lambda characters: [ characters, ]

    @classmethod
    def words_from_text(Word, font_wrapper:FontInstance,
                        text:str, whitespace_codepoint=32,
                        hyphenate_f=None):
        """
        Yield Word objects from `text`, correctly split while taking the
        unicode type of white space and their respective BREAK properties
        into account.
        """
        result = breaking_whitespace_re.split(text)
        it = iter(result)
        while (pair := tuple(itertools.islice(it, 2))):
            if len(pair) == 1:
                word, = pair
                whitespace_codepoint = 32 # Space
            else:
                word, whitespace = pair
                whitespace_codepoint = ord(whitespace[0])

            yield Word(font_wrapper, word,
                       whitespace_codepoint,
                       hyphenate_f)


    def __str__(self):
        return self.word

    def with_hyphen(self):
        return self

    characters_re = re.compile(r"(\w+)(.*)")
    def hyphenate(self):
        """
        Try to hyphenate the word and store the result for syllables()
        below.
        """
        # This is much more complicated than one would think.
        # The hyphenator only knows about regular language words.
        # That’s what we feed him. We keep the rest of the characters
        # and put them back in the result on returning it.
        syllables = None
        match = self.characters_re.match(self.word)
        if match is not None:
            start, extra = match.groups()

            syllables = self._hyphenate_f(start)
            if syllables:
                if extra:
                    # Put the extra characters on the last syllable.
                    syllables[-1] += extra

        if syllables:
            self._syllables = [ Syllable(self.font, [ ord(s) for s in chars ],
                                         space_width=self.space_width)
                                for chars in syllables ]
            self._syllables[-1].final = True
        else:
            self._syllables = ( self, )

        return self._syllables

    @property
    def syllables(self):
        """
        By default return a 1-tuple containing self. If the word has
        been hyphenated, return the result.
        """
        if self._syllables is None:
            return ( self, )
        else:
            return self._syllables

    @property
    def is_hyphenated(self):
        return self._syllables is not None

    @property
    def monosyllabic(self):
        if self._syllables is None:
            self.hyphenate()
        return len(self._syllables) == 1

    def __repr__(self):
        return f"“{self.word}@{self.w:.2f}pt”"

class SoftParagraph(object):
    def __init__(self, words:Sequence[Word], align="left", line_height=None):
        self.words = list(words)
        assert len(self.words) > 0, ValueError(
            "SoftParagraph must not be empty.")

        self.align = align
        self._line_height = line_height

    def clone(self, words):
        return self.__class__(words, self.align, self.line_height)

    @property
    def line_height(self):
        if self._line_height is None:
            return self.words[0].h
        else:
            return self._line_height

    def __repr__(self):
        return f"<{self.__class__.__name__}: “{_pretty_wordlist(self.words)}”>"

class HardParagraph(object):
    def __init__(self, soft_paragraphs:Sequence[SoftParagraph],
                 margin_top:float=0.0, margin_bottom:float=0.0,
                 align="left", dangle_threshold=2):
        self.soft_paragraphs = list(soft_paragraphs)
        assert len(self.soft_paragraphs) > 0, ValueError(
            "HardParagraph must have SoftParagraphs.")

        self.margin_top = margin_top
        self.margin_bottom = margin_bottom

        self.align = align
        self.dangle_threshold = dangle_threshold

    @property
    def line_height(self):
        return self.soft_paragraphs[0].line_height

newline_re_expr = "(?:\r\n|\r|\n)"
single_newline_re = re.compile(newline_re_expr)
multiple_newline_re = re.compile(newline_re_expr + "{2}")
breaking_whitespace_re = re.compile(r"([%s]+)" % breaking_whitespace_chars)
class Text(object):
    def __init__(self, hard_paragraphs):
        self.hard_paragraphs = list(hard_paragraphs)
        assert len(self.hard_paragraphs) > 0, ValueError(
            "Text object must have HardParagraphs.")

    def make_cursor(self):
        return Cursor.make_cursors_for(self, [ "hard_paragraphs",
                                               "soft_paragraphs",
                                               "words", "syllables", ])

    @classmethod
    def from_text(Text,
                  text:str,
                  font:FontInstance,
                  align="left",
                  margin_top=0.0, margin_bottom=0.0, dangle_threshold=2,
                  line_height=None,
                  hyphenate_f=None):
        """
        • Multiple newlines separate hard paragraphs.
        • Single newlines are <br>s: They separate soft paragraphs.
        • Unicode whitespace characters split words unless they are
          marked NO BREAK.
        • Their different widths are adhered to according to the
          unicode_space_characters list in encoding_tables.py
        """

        def soft_paragraphs(text):
            for part in single_newline_re.split(text):
                words = Word.words_from_text(
                    font, part, hyphenate_f=hyphenate_f)
                yield SoftParagraph(words, align, line_height)

        def hard_paragraphs(text):
            for para in multiple_newline_re.split(text):
                yield HardParagraph(soft_paragraphs(para),
                                    margin_top, margin_bottom,
                                    align, dangle_threshold)

        return Text(hard_paragraphs(text))

    def typeset(self, textboxes:Sequence[TextBox]):
        from .typesetting import Typesetter
        typesetter = Typesetter(textboxes, self.make_cursor())
        typesetter.typeset()


def main():
    import pdb, sys, argparse, pathlib

    from hyphen import Hyphenator

    from psbuffer.dsc import Document, Page
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
    document = Document()

    def textboxes():
        width, height = mm(50), mm(100)

        counter = 0
        while True:
            page = document.append(Page(size="a5"))

            left_x = page_margin
            right_x = page.w - page_margin - width

            for x in ( left_x, right_x, ):
                y = page.h - page_margin
                while y - height > 0:
                    tb = page.append(TextBox(x, y-height, width, height,
                                             border=True,
                                             comment="No %i" % counter))
                    yield tb
                    print(tb.comment)
                    print(tb.lines)
                    print()
                    y -= height + mm(6)
                    counter += 1

    cmusr12 = cmusr.make_instance(args.font_size)

    genesis = ("In the beginning God created the heaven and the earth. "
               "And the earth was without form, and void; and darkness "
               "was upon the face of the deep. And the Spirit of God moved "
               "upon the face of the waters. And God said, Let there be "
               "light: and there was light. And God saw the light, that "
               "it was good: and God divided the light from the darkness. "
               "And God called the light Day, and the darkness he called "
               "Night. And the evening and the morning were the first day.")

    genesis_de = ("Am Anfang schuf Gott Himmel und Erde. Und die Erde war  "
                  "wüst und leer, und es war finster auf der Tiefe; und der "
                  "Geist Gottes schwebte auf dem Wasser. Und Gott sprach: Es "
                  "werde Licht! Und es ward Licht. Und Gott sah, daß das "
                  "Licht gut war. Da schied Gott das Licht von der Finsternis "
                  "und nannte das Licht Tag und die Finsternis Nacht. Da ward "
                  "aus Abend und Morgen der erste Tag.")

    # "Well that’s Supercalifragilisticexpialidocious! "
    # "Whatever happens on this line: Don’t Break Me! "


    tests = ( "flexible "
              "And make sure I am not\u202Fbroken\u202Feither. "
              "But\u2000I\u2001am\u2002flexible\u2003and\u2004may\u2005be"
              "\u2006broken!")

    # Whatever happens:
    a = ("Don’t Break Me! "
         "And make very, very sure of it.")
    # Whatever happens:
    b = ("Don’t Break Me! "
         "And make very, very sure of it.")


    # For debugging purposes.
    sp = SoftParagraph(Word.words_from_text(
        cmusr12, tests, hyphenate_f=hyphenator))

    #for line in sp.lines_for(next(textboxes())):
    #    for word in line.words[:-1]:
    #        print(word, end=(" " if word.space_width > 0 else ""))
    #    print(line.words[-1].with_hyphen())

    # genesis + "\n\n" +
    text = Text.from_text(tests, cmusr12,
                          align="block",
                          margin_top=8, hyphenate_f=hyphenator)

    def ps_test():
        try:
            #pdb.set_trace()
            text.typeset(textboxes())
        except TextBoxesExhausted:
            pass

        document.write_to(args.outfile)


    def cursor_test():
        cursor = text.make_cursor()
        for word in cursor:
            print(repr(word))

        print()
        print()

        cursor = text.make_cursor()

        #pdb.set_trace()

        idx = 0
        while True:
            if idx == 4:
                clone = cursor.clone_immutably()

            cursor.hyphenate_current()

            print(repr(cursor.current))

            if not cursor.advance():
                break

            idx += 1


        print()
        print()
        cursor = clone.clone()
        cursor.rewind()
        cursor.rewind()
        cursor.rewind()
        print(cursor.rewind())
        print(cursor.rewind())
        print()
        while True:
            print(repr(cursor.current))

            if not cursor.advance():
                break

        #print()
        #print("1st", clone.first_of("syllables"))
        #print("lst", clone.last_of("syllables"))

        #print()
        #print(repr(cursor.current_of("words")))

        print()
        print()
        # Let’s take a look at Garbage Collection.
        import gc
        gc.collect()
        oldcount = len(gc.get_objects())
        del cursor
        gc.collect()
        newcount = len(gc.get_objects())
        print("Garbage collected on `del cursor`:", oldcount-newcount)


    ps_test()
    # cursor_test()

if __name__ == "__main__":
    main()
