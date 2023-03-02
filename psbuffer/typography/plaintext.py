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
from ..boxes import TextBox, LineBox, TextBoxTooSmall
from ..fonts.fontbase import FontInstance
from ..fonts.encoding_tables import breaking_whitespace_chars

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

    def with_hyphen(self):
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
            print(word.hyphened_width, self.w)
            if word.syllables is None and word.hyphened_width > self.w:
                if self.words:
                    # This line already has a words on it. Stop processing
                    # so the over-sized word may be put on the next line.
                    break

                # The over-sized word is the first and only one on this line.
                self.words.append(word)
                self._h = word.h
                # The word is on the line now and not part of the remainder
                # anymore.
                del self._remainder[0]
                # Stop processing.
                break

            lwidth = ( self.word_space
                       + self.last_space_width
                       + word.hyphened_width)
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

                # If it is not the first word, also add the whitespace
                # width of the previous word.
                if len(self.words) > 0:
                    self.word_space += self.words[-1].space_width

                self.words.append(word)
                self._w = new_width
                self._h = new_height

                # The word has been processed and is removed from the
                # remainder.
                del self._remainder[0]

                # Account for the space the word uses on the line.
                self.word_space += word.w

        # If the last element in words is a syllable that’s not final
        # we need to make sure it has a hyphen and accommodate said hyphen
        # in word_space.
        if not self.words[-1].final:
            self.words[-1] = self.words[-1].with_hyphen()
            self.word_space += self.words[-1].hyphen_width


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

    def on_parent_set(self):
        """
        When added to the textbox, the line is rendered into the the
        body. (It is a boxes.BoxBuffer!)
        """
        line_psrep = bytearray()
        line_displacements = []

        def space_based_modify_displacements_for(word):
            line_displacements[-1] += word.space_width

        if len(self.words) < 2:
            block_gap = 0.0
        else:
            block_gap = (self.w-self.word_space) / (len(self.words)-1)

        def block_modify_displacements_for(word):
            line_displacements[-1] += word.space_width + block_gap

        if self.current_soft_paragraph.align == "left":
            self.print(0, self.y - self.h, "moveto")
            modify_displacements_for = space_based_modify_displacements_for
        elif self.current_soft_paragraph.align == "right":
            self.print(self.w - self.word_space,
                       self.y - self.h, "moveto")
            modify_displacements_for = space_based_modify_displacements_for
        elif self.current_soft_paragraph.align == "center":
            self.print((self.w - self.word_space) / 2.0,
                       self.y - self.h, "moveto")
            modify_displacements_for = space_based_modify_displacements_for
        elif self.current_soft_paragraph.align == "block":
            self.print(0, self.y - self.h, "moveto")
            modify_displacements_for = block_modify_displacements_for
        else:
            raise ValueError(self.current_soft_paragraph.align)

        for word in self.words:
            self.font = word.font
            psrep, displacements = word.xshow_params(self)

            line_psrep.extend(psrep)
            line_displacements.extend(displacements)

            modify_displacements_for(word)

        self.print(ps_literal(line_psrep),
                   ps_literal(line_displacements),
                   "xshow")


    @property
    def font(self):
        return self.textbox._font_instance

    @font.setter
    def font(self, font_instance):
        if self.textbox._font_instance != font_instance:
            font_instance.setfont(self) # Not the textbox!
        self.textbox._font_instance = font_instance

    def __repr__(self):
        return f"<{self.__class__.__name__}: “{_pretty_wordlist(self.words)}”>"

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

    def lines_for(self, textbox, y=None):
        """
        Yield Line objects for `textbox`, starting at `y`, until either all
        words are used up or the textbox would have run out of vertical space.
        """
        if y is None:
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


class TextBoxesExhausted(Exception):
    pass

class TypesettingState(object):
    def __init__(self, parent, textboxes):
        self.parent = parent
        self.textboxes = iter(textboxes)

        # The initiale textbox.
        self._textbox = self.make_textbox()
        self.previous_textbox = None

    @property
    def textbox(self):
        return self._textbox

    @textbox.setter
    def textbox(self, textbox):
        self.previous_textbox = self.textbox
        self._textbox = textbox

    def make_textbox(self):
        """
        Turn StopIteration into TextBoxesExhausted when advancing the
        textboxes iterator.
        """
        try:
            return next(self.textboxes)
        except StopIteration:
            raise TextBoxesExhausted()

    def init_from_hard_paragraph(self, para:HardParagraph):
        # If the current textbox is empty, we ignore the top margin.
        # Otherwise we start with our cursor advanced by the hard
        # paragraph’s margin top.
        if self.textbox.empty:
            self.y = self.textbox.cursor
        else:
            self.y = self.textbox.cursor - para.margin_top

            if self.y <= 0:
                # The margin_top already exhausted the vertical space
                # available. We need a new one.
                self.textbox = self.make_textbox()

                # And we ignore the top margin in the new box.
                self.y = self.textbox.cursor

    def boxbreak(self):
        self.textbox = self.make_textbox()
        self.y = self.textbox.cursor



newline_re_expr = "(?:\r\n|\r|\n)"
single_newline_re = re.compile(newline_re_expr)
multiple_newline_re = re.compile(newline_re_expr + "{2}")
breaking_whitespace_re = re.compile(r"([%s]+)" % breaking_whitespace_chars)
class Text(object):
    def __init__(self, hard_paragraphs):
        self.hard_paragraphs = list(hard_paragraphs)
        assert len(self.hard_paragraphs) > 0, ValueError(
            "Text object must have HardParagraphs.")

    @classmethod
    def from_text(cls,
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

        return cls(hard_paragraphs(text))

    def typeset(self, textboxes:Sequence[TextBox]):
        state = TypesettingState(self, textboxes)

        for para in self.hard_paragraphs:
            state.init_from_hard_paragraph(para)

            # Make a shallow copy of the soft paragraphs.
            soft_paragraphs = list(para.soft_paragraphs)

            while soft_paragraphs:
                sp = soft_paragraphs[0]

                # Make a list of all the lines that might fit into the current
                # textbox.
                lines = list(sp.lines_for(state.textbox, state.y))
                if len(lines) == 0:
                    if state.textbox.empty:
                        # The edge-case first: The line to be rendered next
                        # cannot fit this textbox despite the fact it’s empty.
                        # Bummer. We create a line object that’s as wide as
                        remainder = sp.words[:]
                        word = sp.words[0]

                        # Try to hyphenate the first word.
                        if syllables := word.syllables:
                            # Use the first syllable as our word to typeset.
                            word = syllables[0]
                            # Push the remaining syllables
                            # to the front of the words.
                            remainder[:0] = syllables[1:]

                        # These will by typeset by the next iteration of the
                        # while loop.
                        soft_paragraphs[0] = sp = sp.clone(remainder)

                        self._append_oversized_word_to(word, state.textbox)

                    # We are done with this textbox.
                    state.boxbreak()
                    # We go back to the top of the while loop.
                    continue

                else: # len(lines) > 0
                    # There are lines. See if they’re enough of them.

                    # ORPHAN DETECTION: “A paragraph-opening line that
                    # appears by itself at the bottom of a page or column.”

                    # Walk the set of lines to be rendered backwards. If we
                    # find the first line of the current hard paragraph,
                    # check that it’s not alone.
                    start = len(lines)-1
                    end = start-para.dangle_threshold
                    if end < 2:
                        # We’ll not remove the last to lines from a textbox.
                        end = 2
                    first_line_index = None
                    for a in range( start, end, -1):
                        if lines[a].current_soft_paragraph == \
                           para.soft_paragraphs[0]:
                            first_line_index = a

                    if first_line_index:
                        # See which of the first lines of this
                        # paragraphs from the current textbox without leaving
                        # it (more or less) empty. We’ll remove those lines,
                        # restore them to soft_paragraphs and restart
                        # typesetting to they are set into the next textbox.
                        while len(lines) > first_line_index:
                            first = lines.pop()
                        soft_paragraphs[0] = first.current_soft_paragraph

                    if ( len(soft_paragraphs) == 1 and
                         lines[-1].remainder is None and
                         # We are at the end of this hard paragraph.
                         para.align == "block" ):
                            # If it has block align, the last line must be
                            # rendered with left align.
                            lines[-1].current_soft_paragraph.align = "left"

                    # Add the lines to the textbox
                    # and update soft_paragraphs.
                    state.textbox.typeset(lines)
                    state.y = state.textbox.cursor

                    if (remainder := lines[-1].remainder) is None:
                        # WIDOW DETECTION. “A paragraph-ending line that
                        # falls at the beginning of the following page or
                        # column.”

                        # We are at the end of this soft paragraph.
                        # Is it the last one in this hard paragraph?
                        if ( len(soft_paragraphs) == 1 and
                             # Check for widows.
                             len(lines) < para.dangle_threshold and
                             # Do we evan have a previous textbox?
                             state.previous_textbox is not None ):
                            # How many lines from the previous
                            # textbox can we remove (and re-typeset
                            # into the current one) and still have
                            # a minimum of para.dangle_threshold lines
                            # in it?
                            available = len(state.previous_textbox) - \
                                para.dangle_threshold

                            if available < 0:
                                available = 0

                            last = None
                            for a in range(available):
                                last = state.previous_textbox.pop()

                            # Re-typeset starting with the lines
                            # just removed from the previous textbox.
                            if last:
                                soft_paragraphs[0] = last.current_soft_paragraph
                                #state.boxbreak()
                                state.textbox.clear()
                                state.y = state.textbox.cursor
                                continue

                        del soft_paragraphs[0]
                    else:
                        soft_paragraphs[0] = remainder

                if len(soft_paragraphs) > 0:
                    state.boxbreak()
                # end if len(lines) == 0 or not

            # end while soft_paragraphs

        # end for para in self.hard_paragraphs




    def _append_oversized_word_to(self, word, textbox):
        # Try to fit the syllable by height.
        boxwidth = textbox.line_width_at( textbox.cursor, word.h)
        if boxwidth is None:
            # On failure get the line width for a 0-height line.
            boxwidth = textbox.line_width_at( textbox.cursor, 0)

            if boxwidth is None:
                # This caused by a programming error, but we won’t
                # let max() below throw a TypeError below.
                boxwidth = 0.0

        width = max(word.hyphened_width, boxwidht)
        fake_soft_para = sp.clone([word,])
        fake_textbox = TextBox(0, 0, boxwidth, word.h)

        # Create a line with the over-sized word/syllable on it.
        line = Line(fake_textbox, fake_textbox.cursor, fake_soft_para)

        # Transplant the line to the real textbox.
        line.textbox = textbox
        # Make sure the top of the letters meets the top of the
        # textbox. If not clipped, this will not look pretty.
        line.head.print(0, textbox.h-fake_textbox.h, "transform")
        # Add the line to the textbox…
        textbox.append(line)

        warnings.warn(f"Under-sized textbox “{textbox.comment}”, "
                      f"forced “repr({word})” into it.")



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
        width, height = mm(25), mm(10)

        counter = 0
        while True:
            page = document.append(Page(size="a5"))

            left_x = page_margin
            right_x = page.w - page_margin - width

            for x in ( left_x, right_x, ):
                y = page.h - page_margin
                while y - height > 0:
                    yield page.append(TextBox(x, y-height, width, height,
                                              border=True,
                                              comment="No %i" % counter))
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


    # For debugging purposes.
    sp = SoftParagraph(Word.words_from_text(
        cmusr12, tests, hyphenate_f=hyphenator))

    #for line in sp.lines_for(next(textboxes())):
    #    for word in line.words[:-1]:
    #        print(word, end=(" " if word.space_width > 0 else ""))
    #    print(line.words[-1].with_hyphen())

    text = Text.from_text(genesis + "\n\n" + tests, cmusr12,
                          align="block",
                          margin_top=8, hyphenate_f=hyphenator)

    try:
        #pdb.set_trace()
        text.typeset(textboxes())
    except TextBoxesExhausted:
        pass

    document.write_to(args.outfile)


if __name__ == "__main__":
    main()
