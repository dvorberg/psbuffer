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

import functools, copy, itertools, re, warnings, unicodedata
from typing import Sequence, Iterator

from ..measure import has_dimensions
from ..boxes import TextBox, TextBoxesExhausted
from ..fonts.fontbase import FontInstance
from ..fonts.encoding_tables import breaking_whitespace_chars
from ..utils import pretty_wordlist

from .cursors import Cursor

"""
Classes to represent text formatted with a single FontSpec (font, size,
kerning, char_spacing) throughout.
"""

class Syllable(has_dimensions):
    def __init__(self, font_wrapper:FontInstance, codepoints:Sequence[int],
                 final=False, space_width=None):
        assert len(codepoints), ValueError("Syllables must not be empty.")
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
        return self.font.charwidth(45) #* 0.9 # 45 = “-”

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
        return self.font.line_height

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

            yield Word(font_wrapper, word, whitespace_codepoint, hyphenate_f)


    def __str__(self):
        return self.word

    def with_hyphen(self):
        return self

    characters_re = re.compile(r"(\w+)(.*)")
    soft_hyphen = unicodedata.lookup("SOFT HYPHEN")
    def hyphenate(self):
        """
        Try to hyphenate the word and store the result for syllables()
        below.
        """
        if self.soft_hyphen in self.word:
            # If the word contains a soft hyphen, this is where we split it.
            syllables = self.word.split(self.soft_hyphen)
            # Just in case the soft-hyphen was at the end of the word,
            # we remove empty entries and superflous white space.
            syllables = [ s.strip() for s in syllables ]
            syllables = [ s for s in syllables if s]

            if len(syllables) < 1:
                # Edge-case to prevent exceptions.
                syllables = ( self.word, )
        else:
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
    def __init__(self, words:Sequence[Word], align="left"):
        self.words = list(words)
        assert len(self.words) > 0, ValueError(
            "SoftParagraph must not be empty.")

        self.align = align

    def clone(self, words):
        return self.__class__(words, self.align)

    def __repr__(self):
        return f"<{self.__class__.__name__}: “{pretty_wordlist(self.words)}”>"

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

newline_re_expr = "(?:\r\n|\r|\n)"
single_newline_re = re.compile(r"\s*" + newline_re_expr + r"\s*")
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
                yield SoftParagraph(words, align)

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
    #hyphenator = Hyphenator("en_US").syllables
    # de_DE `language`defaults to 'en_US'
    hyphenator = Hyphenator("en_US").syllables

    page_margin = mm(16)

    # Load the font
    cmusr = Type1(args.outline.open(), args.metrics.open())

    # Create the EPS document
    document = Document()

    def textboxes():
        width, height = mm(50), mm(70)

        counter = 0
        while True:
            page = document.append(Page(size="a5"))

            left_x = page_margin
            right_x = page.w - page_margin - width

            for x in ( left_x, right_x, ):
                y = page.h - page_margin
                while y - height > 0:
                    tb = page.append(TextBox(x, y-height, width, height,
                                             comment="No %i" % counter))

                    tb.head.print("0 0 moveto")
                    tb.head.print(0, tb.h, "lineto")
                    tb.head.print(tb.w, tb.h, "lineto")
                    tb.head.print(tb.w, 0, "lineto")
                    tb.head.print(".95 setgray fill 0 setgray")

                    yield tb
                    y -= height + mm(6)
                    counter += 1

                    if counter > 4:
                        raise TextBoxesExhausted()

    cmusr12 = cmusr.make_instance(args.font_size,
                                  line_height=args.font_size*1.25)

    genesis = ("In the beginning God created the heaven and the earth. "
               "And the earth was without form, and void; and darkness "
               "was upon the face of the deep.\n\n"

               "And the Spirit of God moved upon the face of the waters.\n\n"

               "And God said, Let there be "
               "light: and there was light. And God saw the light, that "
               "it was good: and God divided the light from the darkness. "
               "And God called the light Day, and the darkness he called "
               "Night. And the evening and the morning were the first day.")

    john = unicodedata.normalize(
        "NFC",
        "John 1,1 Ἐν ἀρχῇ ἦν ὁ λόγος, καὶ ὁ λόγος ἦν πρὸς τὸν θεόν, καὶ θεὸς "
        "ἦν ὁ λόγος. 2 οὗτος ἦν ἐν ἀρχῇ πρὸς τὸν θεόν. 3 πάντα διʼ αὐτοῦ "
        "ἐγένετο, καὶ χωρὶς αὐτοῦ ἐγένετο ⸂οὐδὲ :ἕν⸃. ὃ γέγονεν 4 ἐν αὐτῷ ζωὴ "
        "⸀ἦν, καὶ ἡ ζωὴ ἦν τὸ φῶς ⸋τῶν ἀνθρώπων⸌· 5 καὶ τὸ φῶς ἐν τῇ σκοτίᾳ "
        "φαίνει, καὶ ἡ σκοτία αὐτὸ οὐ κατέλαβεν.\n\n"

        "6 Ἐγένετο ἄνθρωπος, ἀπεσταλμένος παρὰ ⸀θεοῦ,⸆ ὄνομα αὐτῷ Ἰωάννης· "
        "7 οὗτος ἦλθεν εἰς μαρτυρίαν ἵνα μαρτυρήσῃ περὶ τοῦ φωτός, ἵνα "
        "πάντες πιστεύσωσιν διʼ αὐτοῦ. 8 οὐκ ἦν ἐκεῖνος τὸ φῶς, ἀλλʼ ἵνα "
        "μαρτυρήσῃ περὶ τοῦ φωτός.\n\n"

        "9 Ἦν τὸ φῶς τὸ ἀληθινόν, ὃ φωτίζει πάντα ἄνθρωπον, ἐρχόμενον εἰς "
        "τὸν κόσμον. 10 ἐν τῷ κόσμῳ ἦν, καὶ ὁ κόσμος διʼ αὐτοῦ ἐγένετο, καὶ "
        "ὁ κόσμος αὐτὸν οὐκ ἔγνω. 11 εἰς τὰ ἴδια ἦλθεν, καὶ οἱ ἴδιοι αὐτὸν "
        "οὐ παρέλαβον. 12 ὅσοι δὲ ἔλαβον αὐτόν, ἔδωκεν αὐτοῖς ἐξουσίαν τέκνα "
        "θεοῦ γενέσθαι, τοῖς πιστεύουσιν εἰς τὸ ὄνομα αὐτοῦ, 13 oοἳ οὐκ ἐξ "
        "αἱμάτων οὐδὲ ἐκ θελήματος σαρκὸς ⸋οὐδὲ ἐκ θελήματος ἀνδρὸς⸌ ἀλλʼ ἐκ "
        "θεοῦ ἐγεννήθησαν.\n\n"

        "14 Καὶ ὁ λόγος σὰρξ ἐγένετο καὶ ἐσκήνωσεν ἐν ἡμῖν, καὶ ἐθεασάμεθα "
        "τὴν δόξαν αὐτοῦ, δόξαν ὡς μονογενοῦς παρὰ πατρός, πλήρης χάριτος "
        "καὶ ἀληθείας.")

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
              "\u2006broken! "
              "More text will create another line.")

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

    # genesis + "\n\n" + tests

    text = ("Hallo Welt,\n"
            "ab hier beginnt Text, der auf mehrere Zeilen umgebrochen wird."
            "\n\n"
            "Ich bin der zweite Absatz.")

    # "soll und der geht hier auch noch weiter.\n"
    #"Hier sollte eine neue Zeile beginnen."

    text = genesis + "\n\n" + tests + "\n\n" + text
    text = Text.from_text(text, cmusr12,
                          align="block", margin_top=8,
                          hyphenate_f=hyphenator)

    def ps_test():
        try:
            #pdb.set_trace()
            text.typeset(textboxes())
        except TextBoxesExhausted:
            raise

        document.write_to(args.outfile)


    def cursor_test():
        cursor = text.make_cursor()

        print("cursor.is_first_of('syllables')",
              cursor.is_first_of('syllables'))
        print("cursor.was_last_of('syllables')",
              cursor.was_last_of('syllables'))
        print("cursor.was_last_of('soft_paragraphs')",
              cursor.was_last_of('soft_paragraphs'))
        print("cursor.was_last_of('hard_paragraphs')",
              cursor.was_last_of('hard_paragraphs'))

        print()

        for counter, word in enumerate(cursor):
            print(repr(word), repr(cursor))

        print()
        print("Anything left in cursor?", bool(cursor))
        print()
        print("cursor.was_last_of('syllables')",
              cursor.was_last_of('syllables'))
        print("cursor.was_last_of('soft_paragraphs')",
              cursor.was_last_of('soft_paragraphs'))
        print("cursor.was_last_of('hard_paragraphs')",
              cursor.was_last_of('hard_paragraphs'))




    ps_test()
    # cursor_test()

if __name__ == "__main__":
    main()
