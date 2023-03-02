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

from ..measure import has_dimensions
from ..boxes import TextBox, LineBox
from ..fonts.fontbase import FontInstance
from ..fonts.encoding_tables import breaking_whitespace_chars

"""
Classes to represent text formatted with a single FontSpec (font, size,
kerning, char_spacing) throughout.
"""

class Syllable(has_dimensions):
    def __init__(self, font_wrapper:FontInstance, codepoints:Sequence[int],
                 final=False, space_width=None):
        self.font = font_wrapper
        self.codepoints = codepoints
        self.final = final
        self._space_width = space_width

        self.last_on_line = None
        self.first_on_line = None

    @functools.cached_property
    def hyphenedWidth(self):
        if self.final:
            return self.w
        else:
            return self.w + self.font.charwidth(45) # 45 = “-”

    def withHyphen(self):
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

    def xshow(self, container):
        return self.font.xshow(container, self.codepoints)

    def __str__(self):
        return "".join([chr(cp) for cp in self.codepoints])

    def __repr__(self):
        return f"-{self}@{self.w:.2f}pt F={self.final}-"

    @property
    def syllables(self):
        # Returning None indicates that this element can’t be hyphenated.
        return None

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
            # No result from the hyphenator.
            return None

    def withHyphen(self):
        return self

    @functools.cached_property
    def syllables(self):
        result = self.hyphenate(self.word)
        if result is None:
            return None
        else:
            ret = [ Syllable(self.font, [ ord(s) for s in chars ],
                             space_width=self.space_width)
                    for chars in result ]
            ret[-1].final = True
            return ret

    def __repr__(self):
        return f"“{self.word}@{self.w:.2f}pt”"

class Line(LineBox):
    def __init__(self, textbox, y, current_soft_paragraph):
        """
        `textbox` – That’s the textbox this Line might be rendered in.
        `y` – The top of the line y-coordinate.
        `current_soft_paragraph` – A SoftParagraph containing the line’s
           words and all those that come after it.
        """
        super().__init__(textbox, y, 0)
        self.current_soft_paragraph = current_soft_paragraph

        # List of words on this line.
        self.words = []

        # List of words that remain in the paragraph after this line.
        self._remainder = current_soft_paragraph.words[:]

        # Space used by the `words` and the whitespace between them.
        self.word_space = 0.0

        while self._remainder:
            word = self._remainder[0]

            # We start by dealing with an edge case: A word/syllable that
            # doesn’t fit a line by itself. It will be typeset and run over
            # the textboxe’s right bound. It may be clipped e.g. by the
            # textbox’s clip= parameter.
            if word.syllables is None and word.hyphenedWidth > self.w:
                if self.words:
                    # This line already has a words on it. Stop processing
                    # so the over-sized word may be put on the next line.
                    break

                # The over-sized word is the first and only one on this line.
                self.words.append(word)
                # The word is on the line now and not part of the remainder
                # anymore.
                del self._remainder[0]
                # Stop processing.
                break

            lwidth = ( self.word_space
                       + self.last_space_width
                       + word.hyphenedWidth)
            if lwidth > self.w:
                # Putting the word on this line would exceed the horizontal
                # space. Can it hyphenate itself?
                if syllables := word.syllables:
                    # The result of hyphenation replaces the word at the
                    # beginning of the remainder.
                    del self._remainder[0]

                    # Prepend the result to `words` and start over.
                    self._remainder[:0] = syllables
                    continue
                else:
                    # This line is full. Stop processing.
                    break
            else:
                # Try to append the word.

                # Appending the word may change this line’s height.
                # Maybe it doesn’t fit the current textbox anymore.
                new_height = word.h
                if new_height > self.h:
                    new_width = textbox.line_width_at(y, new_height)
                    if new_width is None:
                        # This Box won’t fit the current textbox anymore.
                        raise TextBoxTooSmall()

                    # The line would fit the textbox with the new height.
                    # Let’s see if we can place the word on the line
                    # considering the new width.
                    if lwidth > new_width:
                        # Try to hyphenate.
                        if syllables := element.syllables:
                            # As above, the result of hyphanation
                            # replaces the word at the beginning of the
                            # remainder.
                            del self._remainder[0]
                            self._remainder[:0] = syllables

                            # Start over with said result beging first in the
                            # reaminder.
                            continue
                        else:
                            # The word does not fit the line, even if we’d give
                            # it the new height. The line is going to keep its
                            # current width and height and we are done here.
                            break

                # *Do* append the word and set the new width and height.
                self.words.append(word)
                self._w = new_width
                self._h = new_height

                # The word has been processed and is removed from the
                # remainder.
                del self._remainder[0]

                # Account for the space the word uses on the line.
                self.word_space += word.w

                # If it is not the first word, also add the whitespace
                # width of the previous word.
                if len(self.words) > 0:
                    self.word_space += self.words[-1].space_width


    @property
    def remainder(self):
        """
        Return a SoftParagraph that’s just like the input one
        but with only the words in it, that didn’t fit the current line.
        If no words remained (this is the last line of the soft paragraph),
        return None.
        """
        if self._remainder:
            return self.current_soft_paragraph.clone(self._remainder)
        else:
            return None

    @property
    def last_space_width(self):
        """
        Return the width of the last white space character on this line
        or 0.0 if this line is empty.
        """
        if len(self.words) > 0:
            return self.words[-1].space_width
        else:
            return 0.0

    def withHyphen(self):
        """
        Return an exact copy of this line with the last word (maybe)
        hyphenated.
        """
        ret = copy.copy(self)
        ret[-1] = ret[-1].withHyphen()
        return ret
        # ret = self.__class__(self.textbox, self.y,
        #                      self.soft_paragraph, self.is_margin,
        #                      self.border, self.clip, self.comment)

        # if len(self) > 0:
        #     for a in self[:-1]:
        #         ret.append(a)
        #     ret.append(self[-1].withHyphen())

        # return ret


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

    def lines_for(self, textbox):
        """
        Yield Line objects for `textbox`, starting at its cursor,
        until either all words are used up or the textbox would have
        run out of vertical space.
        """
        y = textbox.cursor
        remainder = self
        while remainder is not None:
            try:
                line = Line(textbox, y, remainder)
            except TextBoxTooSmall:
                break

            remainder = line.remainder
            y -= line.h

            yield line

class HardParagraph(object):
    def __init__(self, soft_paragraphs:Sequence[SoftParagraph],
                 margin_top:float=0.0, margin_bottom:float=0.0,
                 align="left", dangle_threshold=2):
        assert len(soft_paragraphs) > 0, ValueError(
            "HardParagraph must have SoftParagraphs.")

        self.soft_paragraphs = list(soft_paragraphs)
        self.margin_top = margin_top
        self.margin_bottom = margin_bottom

        assert align in { "left", "right", "center", }
        self.align = align
        self.dangle_threshold = dangle_threshold

    @property
    def line_height(self):
        return self.soft_paragraphs[0].line_height

    def lineboxes_for(self, textbox):
        """
        Yield TextBox objects that fit into textbox.
        """
        if not textbox.empty and self.margin_top > 0:
            yield textbox.next_linebox(self.margin_top, is_margin="top")

        for sp in self.soft_paragraphs:
            for linebox in sp.lineboxes_for(textbox):
                yield linebox

        if self.margin_bottom > 0:
            yield textbox.next_linebox(self.margin_bottom, is_margin="bottom")

class TextBoxesExausted(Exception):
    pass

class TextBoxTooSmall(Exception):
    """
    A provided Textbox must be able to contain at least as many lines as the
    dangle_threshold demands.
    """
    pass

newline_re_expr = "(?:\r\n|\r|\n)"
single_newline_re = re.compile(newline_re_expr)
multiple_newline_re = re.compile(newline_re_expr + "{2}")
breaking_whitespace_re = re.compile(r"([%s]+)" % breaking_whitespace_chars)
class Text(object):
    def __init__(self, hard_paragraphs):
        assert len(hard_paragraphs) > 0, ValueError(
            "Text object must have HardParagraphs.")
        self.hard_paragraphs = list(hard_paragraphs)

    @classmethod
    def from_string(cls,
                    text:str,
                    font:FontInstance,
                    align="left",
                    margin_top=0.0, margin_bottom=0.0, dangle_threshold=2,
                    line_height=None,
                    hyphenator=None):
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
                    font, part, hyphenate_f=hyphenator)
                yield SoftParagraph(words, align, line_height)

        def hard_paragraphs(text):
            for para in multiple_newline_re.split(text):
                yield HardParagraph(soft_paragraphs(para),
                                    margin_top, margin_bottom,
                                    align, dangle_threshold)

        return cls(hard_paragraphs(text))

    def typeset(self, textboxes:Sequence[TextBox]):
        _skipped = 0

        textboxes = iter(textboxes)

        textbox = next(textboxes)
        for para in self.hard_paragraphs:
            lineboxes = para.lineboxes_for(textbox)

def main():
    import pdb, sys, argparse, pathlib

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
    textbox_a = page.append(TextBox(page_margin, page_margin,
                                    mm(50), page.h - 2*page_margin,
                                    border=True))
    textbox_b = page.append(TextBox(page_margin + mm(70), page_margin,
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

    genesis_de = ("Am Anfang schuf Gott Himmel und Erde. Und die Erde war  "
                  "wüst und leer, und es war finster auf der Tiefe; und der "
                  "Geist Gottes schwebte auf dem Wasser. Und Gott sprach: Es "
                  "werde Licht! Und es ward Licht. Und Gott sah, daß das "
                  "Licht gut war. Da schied Gott das Licht von der Finsternis "
                  "und nannte das Licht Tag und die Finsternis Nacht. Da ward "
                  "aus Abend und Morgen der erste Tag.")

    tests = ( "Well that’s Supercalifragilisticexpialidocious! "
              "Whatever happens on this line: Don’t Break Me! "
              "And make sure I am not\u202Fbroken\u202Feither. "
              "But\u2000I\u2001am\u2002flexible\u2003and\u2004may\u2005be"
              "\u2006broken!")

    # Whatever happens:
    a = ("Don’t Break Me! "
         "And make very, very sure of it.")
    # Whatever happens:
    b = ("Don’t Break Me! "
         "And make very, very sure of it.")


    #text = Text.from_string(genesis + "\n\n" + tests, cmusr12)
    #ext.typeset([textbox_a, textbox_b,])

    document.write_to(args.outfile)

    sp = SoftParagraph(Word.words_from_text(
        cmusr12, tests, hyphenate_f=hyphenator))

    #pdb.set_trace()
    for line in sp.lines_for(textbox_a):
        for word in line.words[:-1]:
            print(word, end=(" " if word.space_width > 0 else ""))
        print(line.words[-1].withHyphen())


if __name__ == "__main__":
    main()
