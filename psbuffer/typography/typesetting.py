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

from typing import Sequence, Iterator

from .cursors import Cursor
from ..boxes import TextBox, LineBox, TextBoxesExhausted, TextBoxTooSmall

class Line(LineBox):
    def __init__(self, textbox, y, cursor):
        """
        `textbox` – That’s the textbox this Line might be rendered in.
        `y` – The top of the line y-coordinate.
        `cursor` – A Cursor object pointing at the first word to be
            typeset on this line.
        """
        super().__init__(textbox, y, 0)
        self.start_cursor = cursor.clone_immutably()

        # List of words on this line.
        self.words = []

        # Space used by the `words` and the whitespace between them.
        self.word_space = 0.0

        self.align = cursor.current_of("soft_paragraphs").align

        for word in cursor:
            # We start by dealing with an edge case: A word/syllable that
            # doesn’t fit a line by itself. It will be typeset and run over
            # the textboxe’s right bound. It may be clipped e.g. by the
            # textbox’s clip= parameter.
            if word.is_hyphenated and word.hyphened_width > self.w:
                # We need to check for textbox space, because it will not
                # happen below.
                if y - word.h < 0:
                    raise TextBoxTooSmall()

                if self.words:
                    # This line already has a words on it. Stop processing
                    # so the over-sized word may be put on the next line.
                    break

                # The over-sized word is the first and only one on this line.
                self.words.append(word)
                self._h = word.h

                # Stop processing.
                break

            lwidth = ( self.word_space
                       + self.last_space_width
                       + word.hyphened_width)
            if lwidth > self.w:
                # Putting the word on this line would exceed the horizontal
                # space. Can it hyphenate itself or is it monosyllabic?
                if word.monosyllabic:
                    # This line is full. Stop processing.
                    break
                else:
                    # Try hyphenating the current word and start over.
                    cursor.hyphenate_current()
                    continue
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
                        if word.monosyllabic:
                            # The word does not fit the line, even if we’d give
                            # it the new height. The line is going to keep its
                            # current width and height and we are done here.
                            break
                        else:
                            # As above, we try to hyphenate the word
                            # and start the process over with its syllables
                            # maybe.
                            cursor.hyphanate_current()
                            continue

                # *Do* append the word and set the new width and height.

                # If it is not the first word, also add the whitespace
                # width of the previous word.
                if len(self.words) > 0:
                    self.word_space += self.words[-1].space_width

                self.words.append(word)
                self._w = new_width
                self._h = new_height

                # Account for the space the word uses on the line.
                self.word_space += word.w

            # We are at the end of a soft paragraph.
            if cursor.was_end_of("soft_paragraph"):
                break

        # If the last element in words is a syllable that’s not final
        # we need to make sure it has a hyphen and accommodate said hyphen
        # in word_space.
        if not self.words[-1].final:
            self.words[-1] = self.words[-1].with_hyphen()
            self.word_space += self.words[-1].hyphen_width

        self.end_cursor = cursor.clone_immutably()

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

        if self.align == "left":
            self.print(0, self.y - self.h, "moveto")
            modify_displacements_for = space_based_modify_displacements_for
        elif self.align == "right":
            self.print(self.w - self.word_space,
                       self.y - self.h, "moveto")
            modify_displacements_for = space_based_modify_displacements_for
        elif self.align == "center":
            self.print((self.w - self.word_space) / 2.0,
                       self.y - self.h, "moveto")
            modify_displacements_for = space_based_modify_displacements_for
        elif self.align == "block":
            self.print(0, self.y - self.h, "moveto")
            modify_displacements_for = block_modify_displacements_for
        else:
            raise ValueError(self.align)

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

class Typesetter(object):
    def __init__(self, textboxes:Sequence[TextBox], cursor:Cursor):
        self.textboxes = iter(textboxes)
        self.cursor = cursor.clone()

        self.textbox = None
        self.previous_textbox = None

        self.boxbreak()

    def boxbreak(self):
        self.previous_textbox = self.textbox
        try:
            self.textbox = next(self.textboxes)
        except StopIteration:
            raise TextBoxesExhausted()

    def typeset(self):
        for element in self.cursor:
            self.hard_paragraph_break()
            self.typeset_hard_paragraph()

    def hard_paragraph_break(self):
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
                self.boxbreak()

                # And we ignore the top margin in the new box.
                self.y = self.textbox.cursor

    def next_lines(self, stop_on):
        while True:
            try:
                yield Line(self.textbox, self.y, self.cursor)
            except TextBoxTooSmall:
                break

            if stop_on():
                break


    def typeset_hard_paragraph(self):
        while True:
            lines = self.next_lines(
                stop_on=lambda: self.cursor.was_end_of("hard_paragraph"))
            lines = list(lines)

            if len(lines) == 0:
                if state.textbox.empty:
                    # The edge-case first: The line to be rendered next
                    # cannot fit this textbox despite the fact it’s empty.
                    # Bummer.
                    self.append_oversized_syllable()

                # We are done with this textbox.
                state.boxbreak()

                # We go back to the top of the while loop.
                continue

            hp = self.cursor.current_of("hard_paragraphs")

            # If `lines` starts with the first line in this paragraph,
            # we want to render at least `dangle threshold` lines.
            if ( lines[0].start_cursor.at_beginning_of("hard_paragraph")
                 and self.orphan_handled(lines, hp.dangle_threshold)):
                continue

            if ( self.cursor.was_end_of("hard_paragraph")
                 and self.widow_handled(lines, hp.dangle_threshold)):
                continue



            if self.cursor.was_end_of("hard_paragraph"):

                if hp.algin == "block":
                    lines[-1].align = "left"

                self.textbox.typeset(lines)

                break

    def append_oversized_syllable(self):
        # Hyphenate for good measure.
        self.cursor.hyphenate_current()

        # Get the over-sized syllable wot work with.
        syllable = self.cursor.current

        # Try to fit the syllable by height.
        boxwidth = self.textbox.line_width_at( self.textbox.cursor,
                                               syllable.h)
        if boxwidth is None:
            # On failure get the line width for a 0-height line.
            boxwidth = textbox.line_width_at( self.textbox.cursor, 0)

            if boxwidth is None:
                # This caused by a programming error, but we won’t
                # let max() throw a TypeError below.
                boxwidth = 0.0

        width = max(syllable.hyphened_width, boxwidht)

        # The syllable will fit this box.
        fake_textbox = TextBox(0, 0, boxwidth, syllable.h)

        # Create a line with the over-sized word/syllable on it.
        line = Line(fake_textbox, fake_textbox.cursor, self.cursor)

        # Transplant the line to the real textbox.
        line.textbox = self.textbox

        # Make sure the top of the letters meets the top of the
        # textbox. If not clipped, this will not look pretty.
        line.head.print(0, textbox.h-fake_textbox.h, "transform")

        # Add the line to the textbox…
        textbox.append(line)

        warnings.warn(f"Under-sized textbox “{textbox.comment}”, "
                      f"forced “repr({syllable})” into it.")


    def orphan_handled(self, prepared_lines, dangle_threshold):
        """
        ORPHAN: “A paragraph-opening line that appears by itself at
        the bottom of a page or column.”

        Reuturn True if an orphan has been handled and typsetting
        has to start over with a new self.cursor.
        """
        if len(prepared_lines) < dangle_threshold: # orphan!
            if self.textbox.empty:
                # If without our current lines the textbox is empty,
                # `dangle threshold` lines are not going to fit anyway.
                # We won’t leave the textbox empty. (This might create a
                # race condition!)
                return False

            self.boxbreak() # A new box, please.
            self.cursor = prepared_lines[0].start_cursor.clone()
            return True
        else:
            return False


    def widow_handled(self, prepared_lines, dangle_threshold):
        """
        WIDOW: “A paragraph-ending line that falls at the
        beginning of the following page or column.”

        Reuturn True if an widow has been handled and typsetting
        has to start over with a new self.cursor.
        """
        # We are at the end of the current hard paragraph.

        # Do we have a widow?
        if len(prepared_lines) - dangle_threshold:
            # Less than `dangle threshold` lines have been prepared for
            # rendering in this box. Can we move words from the
            # previous textbox without leaving it empty?

            # The lines in the previous textbox.
            plines = self.previous_textbox.lines

            # Walk those lines backwards and find the one that’s the first
            # of this hard paragraph, if it is in this textbox.
            idx = len(plines) - 1
            while idx > 0 and not plines[idx].at_beginning_of("hard_paragraph"):
                idx -= 1

            # The number of lines of this hard paragraph
            # in the previous textbox.
            available = len(plines) - idx - 1

            if (len(plines) > 1 # The box must not be empty after removal!
                and available > dangle_threshold):
                removed = plines.pop()

                self.boxbreak()
                self.cursor = removed.start_cursor.clone()

                # This will start typesetting over. If we still have a widow,
                # it will be detected and this will be attempted again.

                return True

        return False
