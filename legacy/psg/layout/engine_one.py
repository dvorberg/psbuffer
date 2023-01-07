#!/usr/bin/env python
# -*- coding: utf-8; mode: python; ispell-local-dictionary: "english"; -*-

##  This file is part of psg, PostScript Generator.
##
##  Copyright 2006-12 by Diedrich Vorberg <diedrich@tux4web.de>
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
This is my first attempt to write a capable layout engine. There are
two phases to this: (1) The user creates a bunch of section
objects. (2) Then these sections are put into columns. The column
informs the section of its width and in return the column tells the
column how much vertical space of the column it wants to use
(returning a pair as (min, max,). The column will then decide how much
vertical space it will supply the section with (supplying at least
min, of course!) and pass a drawing.canvas of the appropriate size to
the sections's draw function. After drawing the section informs the
column about how much vertical space it has used up and if it has
drawn itself completely. It it hasn't, the column will return an
appropriate status to the column factory which will yield a new column
and start over with the unfinished section. If a section *is*
finished, the process starts over with the next section. This should
allow pretty sophisticated stuff.
"""
import sys, types, copy
from string import *

from t4.debug import debug
from t4.psg.drawing import box
from t4.psg.exceptions import EndOfBox
from t4.psg.util import *

class style(dict):
    """
    All lengths in PostScript units, all colors either in PostScript
    commands as a string or None. The font must be a psg.fonts.font
    object or None (in which case the font must be set previously to
    rendering the div. The line-height attribute is a factor applied
    to the font size to determine line height. The border-width is not
    taken into account in calculating the padding and margin values, so
    you have to supply large enough values to avoid overlap.
    """
    
    defaults = { "font": None,             # psg.font.font instance
                 "font-size": 12.0,        # in pt
                 "char-spacing": 0,        # in pt
                 "line-height": 1.0,       # A factor applied to font-size
                 "text-align": "left",     # left, right, justified

                 "vertical-align": "top",  # top, middle, bottom
                 
                 "color": "0 setgray",     # PostScript code to set a color
                 "background-color": None, # PostScript code to set a color

                 "border-color": None,     # PostScript code to set a color
                 "border-left": 0,         # In pt
                 "border-top": 0,          # In pt
                 "border-right": 0,        # In pt
                 "border-bottom": 0,       # In pt
                 
                 "padding-left": 0,        # In pt
                 "padding-top": 0,         # In pt
                 "padding-right": 0,       # In pt
                 "padding-bottom": 0,      # In pt
                 
                 "margin-left": 0,         # In pt
                 "margin-top": 0,          # In pt
                 "margin-right": 0,        # In pt
                 "margin-bottom": 0}       # In pt
                 
    def __init__(self, **attributes):
        dict.update(self, self.defaults)
        
        self._set = set()
        self.update(attributes)
        
        assert self.text_align in ( "left", "right", "justify", )
        assert self.vertical_align in ( "top", "center", "bottom", )

    def __repr__(self):
        if self.has_key("name"):
            name = dict.__getitem__(self, "name")
        else:
            name = str(id(self))
            
        return "<style object named: %s>" % name
        
    def __getattr__(self, name):
        name = replace(name, "_", "-")

        if self.__dict__.has_key("_" + name):
            method = object.__getattr__(self, "_" + name)
            return method()
        elif self.has_key(name):
            return self[name]
        else:
            raise AttributeError(name)

    def __setitem__(self, key, value):
        key = replace(key, "_", "-")

        if key in ("margin", "padding", "border", ):
            self._split_tuple(key, value)
        else:
            dict.__setitem__(self, key, value)
            self._set.add(key)

    def _split_tuple(self, key, tpl):
        for idx, side in enumerate( ("top", "right", "bottom", "left",) ):
            self["%s-%s" % ( key, side, )] = float(tpl[idx])

    def __getitem__(self, key):
        key = replace(key, "_", "-")
        return dict.__getitem__(self, key)

    def update(self, other):
        for key, value in other.iteritems():
            self[key] = value

    def h_margin(self):
        return self.margin_left + self.margin_right

    def v_margin(self):
        return self.margin_top + self.margin_bottom

    def h_padding(self):
        return self.padding_left + self.padding_right

    def v_padding(self):
        return self.padding_top + self.padding_bottom

    def h_border(self):
        return self.border_left + self.border_right

    def v_border(self):
        return self.border_top + self.border_bottom

    def h_fringe(self):
        return self.h_padding() + self.h_border() + self.h_margin()

    def v_fringe(self):
        return self.v_padding() + self.v_border() + self.v_margin()

    def top_fringe(self):
        return self.margin_top + self.border_top + self.padding_top
    
    def right_fringe(self):
        return self.margin_right + self.border_right + self.padding_right
    
    def bottom_fringe(self):
        return self.margin_bottom + self.border_bottom + self.padding_bottom

    def left_fringe(self):
        return self.margin_left + self.border_left + self.padding_left
    
    def __add__(self, other):
        ret = style()
        for a in self._set:
            ret[a] = self[a]
            
        for a in other._set:
            ret[a] = other[a]

        return ret
        
    def word_width(self, word, kerning=True):
        """
        Return the width of WORD when rendered in this style (without
        padding and margin, just the text style).
        """
        if type(word) == types.TupleType:
            return word[1]
        else:
            return self.font.metrics.stringwidth(
                word, self.font_size, kerning, self.char_spacing)

    def words_with_width(self, words, kerning=True):

        if type(words) == types.StringType:
            words = map(unicode, splitfields(words))
        elif type(words) == types.UnicodeType:
            words = splitfields(words)

        ret = []
        for word in words:
            if type(word) == types.TupleType:
                ret.append(word)
            else:
                if type(word) != types.UnicodeType:
                    word = unicode(str(word))
                ret.append( (word, self.word_width(word),) )

        return ret

    def words_width(self, words, kerning=True):
        space_width = self.word_width(u" ")
        return sum(map(lambda tpl: tpl[1],
                       self.words_with_width(words, kerning))) + \
                       (len(words)-1) * space_width

    def div_width(self, words, kerning=True):
        return self.words_width(words, kerning) + self.h_fringe()

    def lines_needed_for(self, words, width, kerning=True, stop_after=None):
        """
        Return the number of lines required to typeset WORDS using
        WIDTH horizontal space. If you need a minimum lines for
        something, use STOP_AFTER to minimize runtime. WORDS may be a
        list of stripped unicode strings or a list of pairs like
        (word, word_width).
        """
        if len(words) == 0:
            return 0
        
        space_width = self.word_width(u" ", kerning)
        
        lines = 1
        cursor = 0        
        for word in words:
            word_width = self.word_width(word, kerning)
                
            if cursor + space_width + word_width > width:
                lines += 1

                if stop_after is not None and lines >= stop_after:
                    return lines
                
                cursor = word_width
            else:
                cursor += space_width + word_width

        return lines
        
    def set_font(self, textbox, line_spacing=0, kerning=True):
        textbox.set_font(font = self.font,
                         font_size = self.font_size,
                         kerning = kerning,
                         alignment = self.text_align,
                         char_spacing = self.char_spacing,
                         line_spacing = line_spacing)
        


        
def run_the_engine(column_factory, section_factory):
    """
    This will run the sections into the columns, yielding the columns.
    """
    section = None
    column = None
    while True:
        if section is None:
            try:
                section = section_factory.next()
            except StopIteration:
                break

        if column is None or column.is_full():
            try:
                column = column_factory.next()
            except StopIteration:
                raise ValueError("Ran out of columns before all sections "
                                 "could be rendered")

        section = column.add_section(section)

def null_canvas(canvas):
    return box.canvas(canvas,
                      0, 0,
                      canvas.w(), canvas.h(),
                      False, False)
        
class column:
    pass

class rectangular_column(column):
    """
    This class uses a drawing.canvas object (directly) to put sections
    on.
    """
    def __init__(self, canvas):
        self._canvas = canvas
        self._remainder = canvas.h()
        self._is_full = False
        self._is_empty = True

    def box(self):
        return self._canvas
        
    def is_full(self): return self._is_full 
    def is_empty(self): return self._is_empty
    def width(self): return self._canvas.w()
    def height(self): return self._canvas.h()
    def remainder(self): return self._remainder

    def add_section(self, section):
        # The test_canvas will not be connected and any PS created will
        # be discarded.
        minimum = section.minimum_height(null_canvas(self._canvas))
        
        if minimum > self.remainder():
            if self.is_empty():
                # It these columns are something else than whole
                # page-sized columns, this may not be what we want to
                # do.
                raise ValueError("Section requested more vertical "
                                 "space than available in an empty "
                                 "column.")
            # We're full by definition
            self._is_full = True
            
            # And return the section as only partially rendered.
            return section

        if self.remainder() == self.height():
            canvas = self._canvas
        else:
            canvas = box.canvas(self._canvas,
                                0, 0, 
                                self._canvas.w(), self.remainder(),
                                border=False, clip=False)
            self._canvas.append(canvas)
            
        self._is_empty = False

        used_vertical_space, done = section.draw(canvas)

        if used_vertical_space > self.remainder():
            raise ValueError("Section used more vertical space than provided "
                             "by the column.")
        self._remainder -= used_vertical_space

        if not done:
            return section
        else:
            return None


class section:
    def reset(self):
        pass

    def minimum_height(self, test_canvas):
        return 0.0
    
    def draw(self, canvas):
        return 0, True

class simple_paragraph(section):
    """
    A simple paragraph section, that will will the supplied canvas
    with text and ignore any other style attributes (margin, padding,
    background and such). Orphans and bastards will be avoided.
    """
    def __init__(self, style, words):
        """
        @param words: A list of stripped unicode strings (the text to
            be rendered).
        """
        # Right on initialization calculate the words widths using the
        # current style.
        self.style = style
        self.words = style.words_with_width(words)
        
        self.lines = None
        self.lines_calculated_for = None

    def reset(self):
        self.lines = None
        self.lines_calculated_for = None        
        
    def minimum_height(self, test_canvas):
        """
        The minimum space is always one line of text.
        """
        self.split_lines(test_canvas)

        if len(self.lines) >= 2:
            # If there are two or more lines, we want to print two lines
            # min, so we won't leave an orphan behind.
            return 2 * self.style.font_size * self.style.line_height
        else:
            # Otherwise, we're satisfied with a single line of print.
            return self.style.font_size * self.style.line_height

    def split_lines(self, canvas):
        width = canvas.w()
        
        if self.lines_calculated_for != width:
            self.lines_calculated_for = width
            if self.lines is None:
                words = self.words
            else:
                # We can get the words still to be typeset from the
                # lines attribute.
                words = []
                for line in self.lines:
                    words += line
                
            # After this, this.lines contains a list of lists of pairs,
            # suitable to be passed to textbox' typeset_line() method.
            space_width = self.style.word_width(u" ")
            column_width = width
            
            self.lines = [[]]
            line_width = 0
            if len(words) > 0 and type(words[-1]) == types.BooleanType:
                words = words[:-1]
            for word, word_width in words:
                tpl = (word, word_width,)
                if line_width + space_width + word_width > column_width:
                    self.lines.append([tpl,])
                    line_width = word_width
                else:
                    self.lines[-1].append(tpl)
                    line_width += space_width + word_width
                    
            self.lines[-1].append(True) # Last line marker
        
        
    def draw(self, canvas):
        if canvas.h() < self.minimum_height(null_canvas(canvas)):
           raise ValueError("The canvas provided was smaller than the "
                             "minimum required vertical space.")

        self.split_lines(canvas)
        tb = box.textbox(canvas, 0, 0, canvas.w(), canvas.h(),
                         border=False)        
        canvas.append(tb)

        line_spacing = ( self.style.line_height * self.style.font_size ) - \
                       self.style.font_size
        
        self.style.set_font(tb)
        
        if self.style.color is not None:
            print >> tb, self.style.color

        room_for = int(canvas.h() /
                       (self.style.font_size * self.style.line_height))
        if room_for >= len(self.lines):
            lines = self.lines
            self.lines = []
        elif room_for == len(self.lines)-1:
            lines = self.lines[:-2]
            self.lines = self.lines[-2:]
        else:
            lines = self.lines[:room_for]
            self.lines = self.lines[room_for:]

        for line in lines:
            if len(line) > 0 and line[-1] == True:
                line = line[:-1]
                last_line = True
            else:
                last_line = False
                
            tb.typeset_line(line, last_line)

            if not last_line:
                try:
                    tb.newline()
                except EndOfBox:
                    pass
            
        return ( tb.text_height(), len(self.lines) == 0, )

class container(section):
    """
    This is a section that contains several sections.
    """
    def __init__(self, sections):
        self._sections = sections[:]
        self.sections = sections[:]

    def reset(self):
        self.sections = self._sections
        for section in self.subsections:
            section.reset()
        
    def minimum_height(self, test_canvas):
        return self.sections[0].minimum_height(test_canvas)

    def draw(self, canvas):
        if len(self.sections) == 0:
            raise ValueError("Container is empty.")

        space_used = 0
        idx = 0
        while self.sections:
            inner = box.canvas(canvas,
                               0, 0,
                               canvas.w(), canvas.h() - space_used,
                               border=False, clip=False)
            canvas.append(inner)

            used, done = car(self.sections).draw(inner)
            space_used += used
            
            if done:
                self.sections = cdr(self.sections)

                # If the remaining space on this canvas is smaller
                # than the next sections's minimum height,
                # we're done here.
                if len(self.sections) > 0 and canvas.h() - space_used < \
                        car(self.sections).minimum_height(null_canvas(canvas)):
                    return space_used, False
            else:
                return space_used, False

        return space_used, True

class wrapper_section(section):
    def __init__(self, subsection):
        self.subsection = subsection

    def reset(self):
        self.subsection.reset()
        
    def minimum_height(self, test_canvas):
        return self.subsection.minimum_height(test_canvas)
        
    def draw(self, canvas):
        return self.subsection.draw(canvas)
    
    def __getattr__(self, name):
        return getattr(self.subsection, name)
    
class style_section(wrapper_section):
    def __init__(self, style, subsection):
        wrapper_section.__init__(self, subsection)
        self.style = style
        self.start = True

    def reset(self):
        self.subsection.reset()
        self.start = True

        
class margin(style_section):
    def minimum_height(self, test_canvas):
        if self.start:
            return self.style.h_margin() + \
                self.subsection.minimum_height(test_canvas)
        else:
            return self.subsection.minimum_height(test_canvas)

    def draw(self, canvas):
        if self.start:
            margin_top = self.style.margin_top
        else:
            margin_top = 0
            
        inner = box.canvas(canvas,
                           self.style.margin_left,
                           0,
                           canvas.w()- self.style.h_margin(),
                           canvas.h()- margin_top,
                           border=False, clip=False)
        
        used_space, done = self.subsection.draw(inner)
        
        if self.start:
            used_space += self.style.margin_top
            
        
        self.start = False
        if done:
            used_space += self.style.margin_bottom
            if used_space > canvas.h():
                used_space = canvas.h()
                
        canvas.append(inner)
        
        return ( used_space, done, )

        
class border(style_section):
    def minimum_height(self, test_canvas):
        if self.start:
            return self.style.border_top + \
                self.subsection.minimum_height(test_canvas)
        else:
            return self.subsection.minimum_height(test_canvas)

    def draw(self, canvas):
        used_space = 0
        
        if self.start:
            height = canvas.h() - self.style.border_top
            used_space = self.style.border_top
        else:
            height = canvas.h()

        inner = box.canvas(canvas,
                           self.style.border_left,
                           0,
                           canvas.w() - self.style.h_border(),
                           height,
                           border=False, clip=False)
        
        used, done = self.subsection.draw(inner)
        used_space += used

        if done:
            used_space += self.style.border_bottom
            if used_space > canvas.h():
                used_space = canvas.h()
                
        if self.style.border_color:
            if self.start and self.style.border_top:
                self.rect( canvas,
                           0, canvas.h(),
                           canvas.w(), canvas.h()-self.style.border_top )
               
            if self.style.border_left:
                self.rect( canvas,
                           0, canvas.h(),
                           self.style.border_left, canvas.h()-used_space )
               
            if self.style.border_right:
                self.rect( canvas,
                           canvas.w(), canvas.h(),
                           canvas.w() - self.style.border_right,
                           canvas.h()- used_space )
               
            if done and self.style.border_bottom:
                self.rect( canvas,
                           canvas.w() - self.style.border_right,
                           canvas.h() - used_space,
                           0,
                           canvas.h() - used_space + self.style.border_bottom)
        canvas.append(inner)

        self.start = False
        return ( used_space, done, )

    def rect(self, canvas, ax, ay, bx, by):
        canvas._( "gsave",
                  "newpath",
                  ax, ay, "moveto",
                  bx, ay, "lineto",
                  bx, by, "lineto",
                  ax, by, "lineto",
                  
                  "closepath",
                  self.style.border_color,
                  "fill",
                  
                  "grestore" )
        

    
class padding(style_section):
    def minimum_height(self, test_canvas):
        if self.start:
            return self.style.padding_top + \
                self.subsection.minimum_height(test_canvas)
        else:
            return self.subsection.minimum_height(test_canvas)

    def draw(self, canvas):
        if self.start:
            height = canvas.h() - self.style.padding_top
            used_space = self.style.padding_top
        else:
            height = canvas.h()
            used_space = 0

        inner = box.canvas(canvas,
                           self.style.padding_left,
                           0,
                           canvas.w() - self.style.h_padding(),
                           height,
                           border=False, clip=False)
        
        used, done = self.subsection.draw(inner)
        used_space += used

        if done:
            used_space += self.style.padding_bottom
            if used_space > canvas.h():
                used_space = canvas.h()
                
        if self.style.background_color:
            ax, ay = 0, canvas.h()
            bx, by = canvas.w(), canvas.h() - used_space
            
            canvas._( "gsave",
                      "newpath",
                      ax, ay, "moveto",
                      bx, ay, "lineto",
                      bx, by, "lineto",
                      ax, by, "lineto",
                      "closepath",
                      self.style.background_color,
                      "fill",
                      "grestore" )
            
        canvas.append(inner)

        self.start = False
        return ( used_space, done, )
        

class fringes(style_section):
    def __init__(self, style, subsection):
        style_section.__init__(self, style, 
                               margin(style,
                                      border(style,
                                             padding(style, subsection))))
    def minimum_height(self, width):
        return self.subsection.minimum_height(width)
        
class paragraph(wrapper_section):
    def __init__(self, style, words):
        wrapper_section.__init__(self,
                                 fringes(style,
                                         simple_paragraph(style, words)))

class headed_section(section):
    def __init__(self, head, body, cont_head=None):
        self.head = head
        self.body = body
        self.cont_head = cont_head
        
        self.start = True

    def reset(self):
        self.start = True
        
        self.head.reset()
        self.body.reset()
        if self.cont_head is not None:
            self.cont_head.reset()
            
    def head_object(self):
        if self.start:
            return self.head
        else:
            if self.cont_head is not None:
                return self.cont_head
            else:
                return None

    def minimum_height(self, test_canvas):
        head = self.head_object()
        
        if head is not None:
            head.minimum_height(test_canvas)
            head_space, done = head.draw(test_canvas)
            head.reset()
        else:
            head_space = 0

        return head_space + self.body.minimum_height(test_canvas)

    def draw(self, canvas):
        head = self.head_object()

        if head is not None:
            head_canvas = box.canvas(canvas,
                                     canvas.x(), canvas.y(),
                                     canvas.w(), canvas.h())
            header_height, done = head.draw(head_canvas)

            canvas.append(head_canvas)
            
            head.reset()
            if not done:
                raise ValueError("Not enough space to draw the header.")
        else:
            header_height = 0

        
        self.start = False

        subcanvas = box.canvas(canvas,
                               0, 0,
                               canvas.w(), canvas.h() - header_height,
                               border=False, clip=False)
        canvas.append(subcanvas)
        space_used, done = self.body.draw(subcanvas)

        return ( header_height + space_used, done, )
        

class table(wrapper_section):
    def __init__(self, style, column_widths, head, *rows):
        wrapper_section.__init__( self,
                                  fringes(style,
                                          simple_table(style,
                                                       column_widths,
                                                       head, 
                                                       *rows)))
    def draw(self, canvas):
        inner = box.canvas(canvas,
                           0, 0,
                           self.width() + self.style.h_fringe(), canvas.h(),
                           border=False, clip=False)
        canvas.append(inner)
        return self.subsection.draw(inner)
    
class simple_table(section):
    def __init__(self, style, column_widths, head, *rows):
        self.style = style
        self.column_widths = column_widths
        
        self.rows = []
        for row in rows:
            self.append(row)
            
        self.head = head
        if self.head is not None:
            if len(self.head) != len(self.column_widths):
                raise ValueError("The head of a table must contain the same "
                                 "number of cells as a regular row.")
            self.head.set_table(self)
        

    def append(self, row):
        if len(row) != len(self.column_widths):
            raise ValueError("Rows for this table must have "
                             "%i cells." % len(self.column_widths))
        row.set_table(self)
        self.rows.append(row)

    def __len__(self):
        return len(self.rows)
        
    def width(self):
        return sum(self.column_widths)

    def predraw(self, canvas):
        if self.head: self.head.predraw(canvas)
        map(lambda row: row.predraw(canvas), self.rows)
        
    def minimum_height(self, canvas):
        self.predraw(canvas)

        if self.head:
            head_height = self.head.height()
        else:
            head_height = 0
            
        return head_height + self.rows[0].height()

    def draw(self, canvas):
        top = canvas.h()

        if self.head:
            top -= self.head.height()
            head_canvas = box.canvas(canvas,
                                     0, top,
                                     canvas.w(), top,
                                     border=False, clip=False)
            canvas.append(head_canvas)
            used_space, done = self.head.draw(head_canvas)
            self.head.reset()
        
        while self.rows:
            req = self.rows[0].height()
            if len(self.rows) == 2: req += self.rows[1].height()
            if top < req:
                return canvas.h() - top, False

            top -= self.rows[0].height()
            
            row_canvas = box.canvas(canvas,
                                    0, top,
                                    canvas.w(), top,
                                    border=False, clip=False)
            canvas.append(row_canvas)
            self.rows[0].draw(row_canvas)
            del self.rows[0]

        return canvas.h() - top, True
        

class row(section):
    def __init__(self, style, *cells):
        self.style = style
        self.table = None

        self.cells = []
        for cell in cells:
            self.append(cell)

    def append(self, cell):
        cell.set_row(self, len(self))
        self.cells.append(cell)

    def __len__(self):
        return len(self.cells)

    def __iter__(self):
        return self.cells.__iter__()

    def __getitem__(self, idx):
        return self.cells[idx]

    def set_table(self, table):
        self.table = table
        for idx, cell in enumerate(self.cells):
            cell.set_row(self, idx)

    def predraw(self, canvas):
        map(lambda cell: cell.predraw(canvas), self.cells)
            
    def height(self):
        return max(map(lambda cell: cell.height(), self))

    def minimum_height(self, canvas):
        return self.height()
    
    def draw(self, canvas):
        if self.style.background_color:
            ax, ay = 0, 0
            bx, by = canvas.w(), self.height()
            
            canvas._( "gsave",
                      "newpath",
                      ax, ay, "moveto",
                      bx, ay, "lineto",
                      bx, by, "lineto",
                      ax, by, "lineto",
                      "closepath",
                      self.style.background_color,
                      "fill grestore")
            

        left = 0
        for cell in self.cells:
            cell_canvas = box.canvas(canvas,
                                     left, 0,
                                     cell.width(), self.height(),
                                     border=False, clip=False)
            cell.draw(cell_canvas)
            canvas.append(cell_canvas)
            left += cell.width()

        return self.height(), True

class cell(section):
    def __init__(self, style, subsection):
        self.style = style
        self.section = subsection
        self.row = None
        self.column_index = -1
        self.canvas = None
        
    def set_row(self, row, column_index):
        self.row = row
        self.table = row.table
        self.column_index = column_index

    def predraw(self, canvas):
        if self.canvas is not None: return
        
        inner_canvas = box.canvas(canvas,
                                  0, 0,
                                  self.table.width()-self.style.h_fringe(),
                                  10000,
                                  border=False, clip=False)
        
        self.section.minimum_height(null_canvas(inner_canvas))
        space_used, done = self.section.draw(inner_canvas)

        self.canvas = box.canvas(canvas,
                                 0, -(inner_canvas.h() - space_used),
                                 self.table.width(), space_used,
                                 border=False, clip=False)
        self.canvas.append(inner_canvas)

    def width(self):
        return self.table.column_widths[self.column_index]

    def height(self):
        return self.canvas.h() + self.style.v_fringe()
    
    def draw(self, canvas):
        section = fringes(self.style, inner_cell(self))
        return section.draw(canvas)
        

class inner_cell(section):
    def __init__(self, cell):
        self.cell = cell
        self.style = cell.style
        self.section = cell.section

    def minimum_height(self, canvas):
        return self.cell.row.height() - self.style.v_fringe()
        
    def draw(self, canvas):
        if self.style.vertical_align == "top":
            padding_top = 0.0
        elif self.style.vertical_align == "middle":
            padding_top = ( canvas.h() - self.height() ) / 2
        elif self.style.vertical_align == "bottom":
            padding_top = ( canvas.h() - self.height() )
        else:
            ValueError(self.style.vertical_align)

        new_canvas = box.canvas(canvas,
                                0,
                                canvas.h() - padding_top - self.cell.canvas.h(),
                                self.cell.width(),
                                self.cell.canvas.h(),
                                border=False, clip=False)
        canvas.append(new_canvas)
        new_canvas.append(self.cell.canvas)
        return self.cell.canvas.h(), True

class raster_image(wrapper_section):
    def __init__(self, style, image, maxsize=None):
        wrapper_section.__init__(
            self, fringes(style, simple_raster_image(image, maxsize)))

class simple_raster_image(section):
    def __init__(self, image, maxsize=None):
        self.image = image
        self.maxsize = maxsize

    def size(self, canvas):
        cw, ch = ( canvas.w(), canvas.h(), )

        if self.maxsize is not None:
            # If the maxsize doesn't fit on the canvas, we use the
            # canvas' dimensions.
            w, h = self.maxsize
            mw, mh = min(w, cw), min(h, ch)
        else:
            mw, mh = cw, ch

        w, h = self.image.size
        w, h = float(w), float(h)

        if w > mw:
            h = h * mw / w
            w = mw
        if h > mh:
            w = w * mh / h
            h = mh

        return (w, h)
        
            
    def minimum_height(self, test_canvas):
        w, h = self.size(test_canvas)
        return h

    def draw(self, canvas):
        image_box = box.raster_image(canvas, self.image,
                                     document_level=True,
                                     border=False, clip=False)
        iw, ih = self.image.size
        iw, ih = float(iw), float(ih)

        w, h = self.size(canvas)
        
        scale_factor = w / iw 
        
        canvas._("gsave",
                 0, canvas.h() - h, "translate",
                 scale_factor, scale_factor, "scale")
        canvas.append(image_box)
        canvas._("grestore")
        
        return h, True
        

        
            

        

        
        

                 
