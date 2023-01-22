#!/usr/bin/python
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
This module defines a number of very usefull classes to model a 'box'
on a page: canvas, textbox, eps_image and raster_image. Textbox
provides a simple multi-line text layout function.
"""

import sys, types
from string import *

from t4 import debug
from t4.uuid import uuid4 as uuid

from t4.psg.document import document
from t4.psg.exceptions import *
from t4.psg.util import *
from t4.psg.fonts import font as font_cls

# For car and cdr refer to your favorite introduction to LISP. The
# Lisp Tutorial built in to your copy of Emacs makes a good start.
# I know this may not be everyone's taste in programming. But it's
# *so* elegant... ;-)

class box:
    """
    A box is a rectengular area on a page. It has a position on the
    page, a width, and a height. In other words: A bounding box. The
    box class provides a mechanism to store PostScript code: It
    maintinas lists called head, body and tail, which contain
    PostScript statements to draw the box's content. The PostScript
    you use is arbitrary with one exceptions: code produced by the box
    is supposed to restore the PostScript graphic context to the same
    state it encountered it in. That's why it unconditionally push()es
    a gsave/grestore pair to its buffers.

    A box' coordinates and size are not mutable. They are accessible
    through the x(), y(), w() and h() method returning position, width
    and height respectively.

    The box class provides two alternative constructors: from_bounding_box
    and from_center.
    """
    def __init__(self, parent, x, y, w=0, h=0, border=False, clip=False,
                 comment=""):
        """
        Construct a box with lower left corner (x, y), with w and
        height h.

        @param parent: Either a page or a box object that contains this
           box.
        @param border: Boolean that determines whether the box will draw a
           hair line around its bounding box.
        @param clip: Boolean indicating whether the bounding box shall
           establish a clipping path around its bounding box.
        """
        self.set_parent(parent)
        self._w = float(w)
        self._h = float(h)
        self._x = float(x)
        self._y = float(y)
        self._border = border
        self._clip = clip

        self.head = file_like_buffer()
        self.body = file_like_buffer()
        self.tail = file_like_buffer()

        cmt = "%s: %s\n" % (self.__class__.__name__, comment)
        self.push("gsave % begin " + cmt,
                  "grestore % end " + cmt)

        if border:
            self.print_bounding_path()
            # Set color to black, line type to solid and width to 'hairline'
            print >> self.head, "0 setgray [] 0 setdash .1 setlinewidth"
            # Draw the line
            print >> self.head, "stroke"

        if clip:
            self.print_bounding_path()
            print >> self.head, "clip"

    def from_bounding_box(cls, parent, bb, border=False, clip=False):
        """
        Initialize a box from its bounding box.

        @param bb: The bounding box.
        @type bb: psg.util.bounding_box instance.
        """
        return cls(parent, bb.llx, bb.lly, bb.width(), bb.height(),
                   border, clip)
    from_bounding_box = classmethod(from_bounding_box)

    def from_center(cls, parent, x, y, w, h, border=False, clip=False):
        """
        For this constructor (x, y) is not the lower left corner of
        the box but its center.
        """
        return cls(parent, x - w/2.0, y - h/2.0, w, h, border, clip)
    from_center = classmethod(from_center)


    def get_parent(self):
        return self._parent

    def set_parent(self, parent):
        if parent is None:
            self.page = None
            self.document = None
        elif isinstance(parent, (box, canvas,)):
            self.page = parent.page
            self.document = parent.document
        elif isinstance(parent, document.page):
            self.page = parent
            self.document = parent.document
        elif isinstance(parent, document.document):
            self.page = None
            self.document = parent
        else:
            raise ValueError("parent= must be a page, a box object or None.")

        self._parent = parent

    parent = property(get_parent, set_parent)

    def x(self): return self._x
    def y(self): return self._y
    def w(self): return self._w
    def h(self): return self._h

    def bounding_box(self):
        """
        Return the box' bounding box as a util.bounding_box instance.
        """
        return bounding_box(self._x, self._y, self._x+self._w, self._y+self._h)

    def push(self, for_head, for_tail=None):
        """
        Append for_head to head and prepent(!) for_tail to tail. If
        for_head and for_tail do not end in whitespace, push() will
        append a Unix newline to them before adding them to the
        buffer.
        """
        for_head = str(for_head)
        if len(for_head) > 0 and for_head[-1] not in "\n\t\r ":
            for_head += "\n"

        self.head.append(for_head)

        if for_tail is not None:
            if len(for_tail) > 0 and for_tail[-1] not in "\n\t\r ":
                for_tail += "\n"

            self.tail.prepend(for_tail)

    def write(self, what):
        """
        Write to the box' body.
        """
        self.body.write(what)

    def _(self, *stuff):
        self.body._(*stuff)

    def add_resource(self, resource, document_level=True):
        """
        Add a resource to the current document (document_level=True,
        the default) or page (document_level=False) using the page's
        add_resource function.
        """
        if not self.page or document_level:
            self.document.add_resource(resource)
        else:
            self.page.add_resource(resource, document_level)


    def write_to(self, fp):
        """
        Write the box' content to file pointer fp.
        """
        self.head.write_to(fp)
        self.body.write_to(fp)
        self.tail.write_to(fp)

    def print_bounding_path(self):
        # Set up a bounding box path
        print >> self.head, "newpath"
        print >> self.head, "%f %f moveto" % ( self.x(), self.y(), )
        print >> self.head, "%f %f lineto" % ( self.x(),
                                               self.y() + self.h(), )
        print >> self.head, "%f %f lineto" % ( self.x() + self.w(),
                                               self.y() + self.h(), )
        print >> self.head, "%f %f lineto" % ( self.x() + self.w(),
                                               self.y(), )
        print >> self.head, "closepath"

    def append(self, what):
        self.body.append(what)

    write = append

class canvas(box):
    """
    A canvas is a bow to draw on. By now the only difference to a box
    is that it has its own coordinate system. PostScript's translate
    operator is used to relocate the canvas' origin to its lower left
    corner.
    """

    def __init__(self, parent, x, y, w=0, h=0,
                 border=False, clip=False, comment="", **kw):
        box.__init__(self, parent, x, y, w, h, border, clip, comment)

        # Move the origin to the lower left corner of the bounding box
        if self.x() != 0 or self.y() != 0:
            print >> self.head, "%f %f translate" % ( self.x(), self.y(), )

class textbox(canvas):
    """
    A rectengular area on the page you can fill with paragraphs of
    text written in a single font.
    """
    SOFT_NEWLINE = r"\n"

    def __init__(self, parent, x, y, w, h,
                 border=False, clip=False, comment="", **kw):
        canvas.__init__(self, parent, x, y, w, h, border, clip, comment)
        self._line_cursor = h
        self.set_font(None)

    def set_font(self, font, font_size=10, kerning=True,
                 alignment="left", char_spacing=0.0, line_spacing=0,
                 paragraph_spacing=0, tab_stops=()):
        """
        @param font: A psg.font.font or psg.document.font_wrapper instance.
           If a font instance is provided, the font will be registered with
           this box' page and installed at document level
           (see page.register_font() for details).
        @param font_size: Font size in PostScript units. (default 10)
        @param kerning: Boolean indicating whether to make use of kerning
           information from the font metrics if available.
        @param alignment: String, one of 'left', 'right', 'center', 'justify'
        @param char_spacing: Space added between each pair of chars,
           in PostScript units
        @param line_specing: Space between two lines, in PostScript units.
           Line height = font_size + line_spacing.
        @param paragraph_spacing: Distance between two paragraphs.
        @param tab_stops: Collection of pairs as (distance, 'dir') with
           distance the distance from the last tab stop (there is always one on
           0.0) and 'dir' being one of 'l', 'r', 'c' meaning left, right,
           center, respectively. THIS IS NOT IMPLEMENTED, YET!!!
        """
        self.font_size = float(font_size)
        self.kerning = kerning
        assert alignment in ( "left", "right", "center", "justify", )
        self.alignment = alignment
        self.char_spacing = float(char_spacing)
        self.line_spacing = float(line_spacing)
        self.paragraph_spacing = float(paragraph_spacing)
        self.tab_stops = tab_stops

        if font is not None:
            if isinstance(font, font_cls):
                self.font_wrapper = self.document.register_font(font)

            elif isinstance(font, document.font_wrapper):
                self.font_wrapper = font

            else:
                raise TypeError("The font must be provided as a "
                                "psg.fonts.font or "
                                "psg.document.font_mapper instance.")

            print >> self, "/%s findfont" % self.font_wrapper.ps_name()
            print >> self, "%f scalefont" % self.font_size
            print >> self, "setfont"

            # Cursor
            try:
                if self.font_wrapper is not None: self.newline()
            except EndOfBox:
                raise BoxTooSmall("The box is smaller than the line height.")

            self.space_width = self.font_wrapper.font.metrics.stringwidth(
                " ", self.font_size)

    def typeset(self, text, hyphenator=None):
        r"""
        Typeset the text into the text_box. The text must be provided
        as a Unicode(!) string. Paragraphs are delimited by Unix
        newlines (\n), otherwise any white space is treated as a
        single space (like in HTML or TeX). The function will return
        any text that did not fit the box as a (normalized) Unicode
        string. No hyphanation will be performed.
        """
        if type(text) != UnicodeType:
            raise TypeError("typeset() only works on unicode strings!")

        paragraphs = split(text, "\n")
        paragraphs = filter(lambda a: strip(a) != "", paragraphs)
        paragraphs = map(splitfields, paragraphs)
        # Paragraphs is now a list of lists containing words (Unicode strings).

        paragraphs = self.typeset_paragraphs(paragraphs, hyphenator)

        if len(paragraphs) > 0:
            paragraphs = map(lambda l: join(l, " "), paragraphs)
            paragraphs = filter(lambda a: a != "", paragraphs)
            paragraphs = join(paragraphs, "\n")
            return paragraphs
        else:
            return ""

    def typeset_paragraphs(self, paragraphs, hyphenator=None):
        """
        @param paragraphs: A list of lists of stripped unicode
           strings to by typeset into the textbox.
        @returns: Those paragraphs that could not be rendered.
        """
        while(paragraphs):
            paragraph = car(paragraphs)
            paragraphs = cdr(paragraphs)
            paragraph = self.typeset_paragraph(paragraph, hyphenator)
            if len(paragraph) != 0:
                paragraphs.insert(0, paragraph)
                return paragraphs

            if len(paragraphs) > 0:
                try:
                    self.newline()
                except EndOfBox:
                    return paragraphs

        return []

    def typeset_paragraph(self, paragraph, hyphenator):
        """
        @param paragraph: A list of stripped unicode strings.
        @returns: A list of unicode strings that could not be typeset.
        """
        if self.font_wrapper is None:
            raise IllegalFunctionCall("You must call set_font() before "
                                      "typesetting any text.")

        line = []
        line_width = 0
        while(paragraph):
            word = car(paragraph)
            if word == self.SOFT_NEWLINE:
                if len(line) > 0: self.typeset_line(line)
                return cdr(paragraph)

            if type(word) == types.TupleType:
                word, word_width = word
            else:
                word_width = self.word_width(word)

            if line_width + word_width > self.w():
                if hyphenator is not None:
                    syllables = hyphenator(word)

                    if len(syllables) > 1:
                        word = []
                        while syllables:
                            word.append(car(syllables))
                            syllables = cdr(syllables)

                            w = join(word, "") + "-"
                            ww = self.word_width(w)

                            if line_width + ww > self.w():
                                if len(word) == 1:
                                    break # Typeset the line and set
                                          # the word one the next
                                          # line.
                                else:
                                    # Remove the last syllable from the word.
                                    syllables.insert(0, word.pop())

                                    # Add the fitting syllables + "-" to the
                                    # current line.
                                    w = join(word, "") + "-"
                                    line.append( (w, self.word_width(w),) )

                                    # Remove the partially rendered word from
                                    # the paragraph.
                                    paragraph = cdr(paragraph)

                                    # If the remaining word is too
                                    # wide for the box, we can't just
                                    # push it to the paragraph and
                                    # re-loop, we have to render it
                                    # partial on the next line.
                                    w = join(syllables, "")
                                    ww = self.word_width(w)
                                    if ww > self.w():
                                        try:
                                            # Next line...
                                            self.newline()

                                            # render the remainder of
                                            # the word, overlapping our
                                            # right border if it so be.
                                            line = [ (w, ww,) ]
                                            self.typeset_line(line)
                                        except EndOfBox:
                                            # Hand the problem back to
                                            # the caller.
                                            paragraph.insert(0, w)
                                    else:
                                        # Add the remaining syllables to the
                                        # beginning of the paragraph for the
                                        # next line.
                                        paragraph.insert(0, w)

                                    break
                    else:
                        if word_width > self.w():
                            self.typeset_line(line)
                            try:
                                self.newline()
                            except EndOfBox:
                                paragraph.insert(0, word)
                                return paragraph

                            line = [ (word, word_width,) ]
                            paragraph = cdr(paragraph)

                self.typeset_line(line)
                try:
                    self.newline()
                except EndOfBox:
                    return paragraph

                line = []
                line_width = 0
            else:
                line.append( (word, word_width,) )
                line_width += word_width + self.space_width
                paragraph = cdr(paragraph)

        # Render the last line.
        if len(line) != 0:
            self.typeset_line(line, True)

        try:
            self.advance(self.paragraph_spacing)
        except EndOfBox:
            pass

        return []

    def word_width(self, word):
        return self.font_wrapper.font.metrics.stringwidth(
            word, self.font_size, self.kerning, self.char_spacing)

    def typeset_line(self, words, last_line=False):
        """
        Typeset words on the current coordinates. Words is a list of pairs
        as ( 'word', width, ).
        """
        if False: #debug.debug.verbose:
            print >> self, "gsave"
            print >> self, "newpath"
            print >> self, "0 %f moveto" % self._line_cursor
            print >> self, "%f %f lineto" % ( self.w(), self._line_cursor, )
            print >> self, "0.33 setgray"
            print >> self, "[5 5] 0 setdash"
            print >> self, "stroke"
            print >> self, "grestore"

        chars = []
        char_widths = []

        word_count = len(words)

        while(words):
            word, word_width = car(words)
            words = cdr(words)

            if type(word) != UnicodeType:
                raise TypeError("Postscript strings must be "
                                "unicode. " + repr(word))

            for idx in range(len(word)):
                try:
                    char = ord(word[idx])
                except TypeError:
                    print repr(words)
                    raise

                if self.kerning:
                    try:
                        next = ord(word[idx+1])
                    except IndexError:
                        next = 0

                    kerning = self.font_wrapper.font.metrics.kerning_pairs.get(
                        ( char, next, ), 0.0)
                    kerning = kerning * self.font_size / 1000.0
                else:
                    kerning = 0.0

                if idx == len(word) - 1:
                    spacing = 0.0
                else:
                    spacing = self.char_spacing

                char_width = self.font_wrapper.font.metrics.stringwidth(
                    unichr(char), self.font_size) + kerning + spacing

                chars.append(char)
                char_widths.append(char_width)

            # The space between...
            if words: # if it's not the last one...
                chars.append(32) # space
                char_widths.append(None)

        line_width = sum(filter(lambda a: a is not None, char_widths))

        if self.alignment in ("left", "center", "right",) or \
               (self.alignment == "justify" and last_line):
            space_width = self.font_wrapper.font.metrics.stringwidth(
                " ", self.font_size)
        else:
            space_width = (self.w() - line_width) / float(word_count-1)


        n = []
        for a in char_widths:
            if a is None:
                n.append(space_width)
            else:
                n.append(a)
        char_widths = n

        # Horizontal displacement
        if self.alignment in ("left", "justify",):
            x = 0.0
        elif self.alignment == "center":
            line_width = sum(char_widths)
            x = (self.w() - line_width) / 2.0
        elif self.alignment == "right":
            line_width = sum(char_widths)
            x = self.w() - line_width

        # Position PostScript's cursor
        print >> self, "%f %f moveto" % ( x, self._line_cursor, )

        char_widths = map(lambda f: "%.2f" % f, char_widths)
        tpl = ( self.font_wrapper.postscript_representation(chars),
                    join(char_widths, " "), )
        print >> self, "(%s) [ %s ] xshow" % tpl

    def newline(self):
        """
        Move the cursor downwards one line. In debug mode (psg.debug.debug
        is set to verbose) this function will draw a thin gray line below
        every line. (No PostScript is generated by this function!)
        """
        self.advance(self.line_height())

    def line_height(self):
        """
        Return the height of one line (font_size + line_spacing)
        """
        return self.font_size + self.line_spacing

    def advance(self, space):
        """
        Advance the line cursor downward by space. (No PostScript is
        generated by this function, it only updates an internal
        value!)
        """
        self._line_cursor -= space

        if self._line_cursor < 0:
            raise EndOfBox()

    def text_height(self):
        """
        The height of the text rendered so far.
        """
        if self._line_cursor < 0:
            l = 0
        else:
            l = self._line_cursor

        return self.h() - l

    def fit_height(self):
        """
        Fit the bounding box of the textbox to the text_height. The
        last line's first letter will be on 0,0.
        """
        if self.h() != self.text_height():
            print >> self.head, "0 -%f translate %% fit_height" % (
                self.h() - self.text_height())
            self._h = self.text_height()

class _eps_image(box):
    """
    This is the base class for eps_image and raster_image below, which
    both embed external images into the target document as a Document
    section.
    """
    def __init__(self, parent, subfile, bb, document_level,
                 border, clip, comment):
        box.__init__(self, parent, bb.llx, bb.lly, bb.width(), bb.height(),
                     border, clip, comment)

        if document_level:
            # If the EPS file is supposed to live at document level,
            # we create a file resource in its prolog.

            # The mechanism was written and excellently explained by
            # Thomas D. Greer at http://www.tgreer.com/eps_vdp2.html .
            identifyer = "psg_eps_file*%i" % self.document.embed_counter()
            file_resource = self.document.file_resource(str(uuid())+".eps")
            print >> file_resource, "/%sImageData currentfile" % identifyer
            print >> file_resource, "<< /Filter /SubFileDecode"
            print >> file_resource, "   /DecodeParms << /EODCount"
            print >> file_resource, "       0 /EODString (***EOD***) >>"
            print >> file_resource, ">> /ReusableStreamDecode filter"
            file_resource.append(subfile)
            print >> file_resource, "***EOD***"
            print >> file_resource, "def"

            print >> file_resource, "/%s " % identifyer
            print >> file_resource, "<< /FormType 1"
            print >> file_resource, "   /BBox [%f %f %f %f]" % bb.as_tuple()
            print >> file_resource, "   /Matrix [ 1 0 0 1 0 0]"
            print >> file_resource, "   /PaintProc"
            print >> file_resource, "   { pop"
            print >> file_resource, "       /ostate save def"
            print >> file_resource, "         /showpage {} def"
            print >> file_resource, "         /setpagedevice /pop load def"
            print >> file_resource, "         %sImageData 0 setfileposition"%\
                                                                     identifyer
            print >> file_resource, "            %sImageData cvx exec"%\
                                                                     identifyer
            print >> file_resource, "       ostate restore"
            print >> file_resource, "   } bind"
            print >> file_resource, ">> def"

            # Store the ps code to use the eps file in self
            print >> self, "%s execform" % identifyer
        else:
            from t4.psg import procsets

            self.add_resource(procsets.dsc_eps)
            print >> self, "psg_begin_epsf"
            print >> self, "%%BeginDocument"
            self.append(subfile)
            print >> self
            print >> self, "%%EndDocument"
            print >> self, "psg_end_epsf"

    def fit(self, canvas):
        """
        Fit this image into `canvas` so that it will set at (0,0) filling
        as much of the canvas as possible.  Return the size of the
        scaled image as a pair of floats (in PostScript units).
        """
        w = canvas.w()
        factor = w / self.w()
        h = self.h() * factor

        if h > canvas.h():
            h = canvas.h()
            factor = h / self.h()
            w = self.w() * factor

        print >> canvas, "gsave"
        print >> canvas, factor, factor, "scale"
        canvas.append(self)
        print >> canvas, "grestore"

        return w, h,

class eps_image(_eps_image):
    """
    Include a EPS complient PostScript document into the target
    PostScript file.
    """
    def __init__(self, parent, fp, document_level=False,
                 border=False, clip=False, comment=""):
        """
        @param fp: File pointer opened for reading of the EPS file to be
           included
        @param document_level: Boolean indicating whether the EPS file shall
           be part of the document prolog and be referenced several times from
           within the document, or if it shall be included where it is used
           for a single usage.
        """

        if isinstance(parent, document.document):
            document_level = True

        fp = eps_file_without_preview(fp)
        bb = get_eps_bb(fp)
        fp.seek(0)

        if not isinstance(fp, subfile._subfile):
            fp = file_as_buffer(fp)

        _eps_image.__init__(self, parent, fp,
                            bb, document_level,
                            border, clip, comment)


class raster_image(_eps_image):
    """
    This class creates a box from a raster image. Any image format
    supported by the Python Image Library is supported. The class uses
    PIL's EPS writer to create a PostScript representation of the
    image, which is much easier to program and much faster than
    anything I could have come up with, and uses PIL's output with the
    _eps_image class above. Of course, as any other part of psg, this
    is a lazy peration. When opening an image with it, PIL only reads
    the image header to determine its size and color depth. Conversion
    of the image takes place on writing.

    This assumes 72dpi raster images. Use _eps_image.fit() if needed.
    """
    class raster_image_buffer:
        def __init__(self, pil_image):
            self.pil_image = pil_image

        def write_to(self, fp):
            self.pil_image.save(fp, "EPS")

    def __init__(self, parent, pil_image, document_level=False,
                 border=False, clip=False, comment=""):
        """
        @param pil_image: Instance of PIL's image class
        @param document_level: Boolean indicating whether the EPS file shall
           be part of the document prolog and be referenced several times from
           within the document or if it shall be included where it is used
           for a single usage.
        """
        width, height = pil_image.size
        bb = bounding_box(0, 0, width, height)

        if pil_image.mode != "CMYK":
            pil_image = pil_image.convert("CMYK")

        fp = self.raster_image_buffer(pil_image)

        _eps_image.__init__(self, parent, fp, bb, document_level,
                            border, clip, comment)

class wmf_file(_eps_image):
    """
    This class creates a box from a Windows Meta File.
    """
    def __init__(self, parent, wmf_fp, document_level=False,
                 border=False, clip=False, comment=""):

        eps = wmf2eps(wmf_fp)

        bb = eps.bounding_box
        bb = bounding_box.from_tuple(bb)

        _eps_image.__init__(self, parent, eps, bb, document_level,
                            border, clip, comment)
