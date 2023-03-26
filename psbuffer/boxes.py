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

from uuid import uuid4 as uuid
from typing import Sequence

from .base import encode, PSBuffer, FileWrapper
from .dsc import DSCBuffer, ResourceSection, Comment
from .measure import Rectangle
from .utils import eps_file_without_preview, get_eps_bb
from . import procsets

class BoxBuffer(DSCBuffer):
    def __init__(self):
        super().__init__()

        self.head = DSCBuffer()
        self.head.parent = self

        self.tail = DSCBuffer()
        self.tail.parent = self

    def write_to(self, fp):
        self.head.write_to(fp)
        super().write_to(fp)
        self.tail.write_to(fp)

    def push(self, for_head, for_tail=None):
        """
        Append for_head to head and prepent(!) for_tail to tail. If
        for_head and for_tail do not end in whitespace, push() will
        append a Unix newline to them before adding them to the
        buffer.
        """
        if for_head:
            for_head = self._convert(for_head)
            if for_head[-1] not in b"\n\t\r ":
                for_head += b"\n"

            self.head.write(for_head)

        if for_tail:
            for_tail = self._convert(for_tail)
            if for_tail[-1] not in b"\n\t\r ":
                for_tail = for_tail + b"\n"

            self.tail.prepend(for_tail)


class Box(BoxBuffer, Rectangle):
    def __init__(self, x, y, w, h, border=False, clip=False, comment=""):
        BoxBuffer.__init__(self)
        Rectangle.__init__(self, x, y, w, h)

        self.border = border
        self.clip = clip
        self.comment = comment

        self._font_instance = None

    @property
    def font(self):
        return self._font_instance

    @font.setter
    def font(self, font_instance):
        if self._font_instance != font_instance:
            font_instance.setfont(self)
        self._font_instance = font_instance

    @property
    def _rich_comment(self):
        return "%s: %s" % (self.__class__.__name__, self.comment)

    def write_to(self, fp):
        self.write_prolog_to(fp)

        ec = encode(self._rich_comment) + b"\n"
        fp.write(b"% begin " + ec)
        super().write_to(fp)
        fp.write(b"% end " + ec)

    def write_prolog_to(self, fp):
        if not self.border and not self.clip:
            return

        prolog = DSCBuffer()
        print = prolog.print
        comment = self._rich_comment

        print("% begin prolog of", comment)

        if self.border:
            print("gsave % border=True")
            self._print_bounding_path(print)

            if type(self.border) is tuple:
                color, linewidth = self.border
            else:
                color = "0 setgray"
                linewidth = ".1"
            # Set color to black, line type to solid and width to 'hairline'
            # "[] 0 setdash",
            print(color, linewidth, " setlinewidth")

            # Draw the line
            print("stroke")
            print("grestore % border=True")

        if self.clip:
            self._print_bounding_path(print)
            head.print("clip % clip=True")

        print("% end prolog of", comment)

        prolog.write_to(fp)


    def _print_bounding_path(self, print):
        # Set up a bounding box path
        print("newpath")
        print(self.x,          self.y,          "moveto")
        print(self.x,          self.y + self.h, "lineto")
        print(self.x + self.w, self.y + self.h, "lineto")
        print(self.x + self.w, self.y,          "lineto")
        print("closepath")

class IsolatedBox(Box):
    """
    This box adds a gsave/grestore pair at the very beginning and end
    of its content.
    """
    def write_to(self, fp):
        self.write_prolog_to(fp)

        ec = encode(self._rich_comment) + b"\n"
        fp.write(b"gsave % begin " + ec)
        BoxBuffer.write_to(self, fp)
        fp.write(b"grestore % end " + ec)

class Canvas(IsolatedBox):
    """
    A canvas is a bow to draw on. By now the only difference to a box
    is that it has its own coordinate system. PostScript's translate
    operator is used to relocate the canvas' origin to its lower left
    corner.
    """
    def __init__(self, x, y, w, h,
                 border=False, clip=False, comment=""):
        super().__init__(x, y, w, h, border, clip, comment)

        # Move the origin to the lower left corner of the bounding box
        if x != 0 or y != 0:
            self.head.print(self.x, self.y, "translate",
                            " % ", self._rich_comment)


class EPSBox(IsolatedBox):
    """
    This is the base class for eps_image and raster_image below, which
    both embed external images into the target document as a Document
    section.
    """
    def __init__(self, subfile, bb, document_level, border, clip, comment):
        super().__init__(bb.llx, bb.lly, bb.w, bb.h, border, clip, comment)
        self.subfile = FileWrapper(subfile)
        self.document_level = document_level
        self.resource_identifyer = None
        self._used = False

    def on_parent_set(self):
        if self.resource_identifyer is None:
            self.resource_identifyer = str(uuid())+".eps"
            self._initialize_resource()
        else:
            if not self.document_level:
                raise IOError("When using an EPSBox more than once, "
                              "use document_level=True to avoid output "
                              "of multiple redundant copied.")

    def _initialize_resource(self):
        if self.document_level:
            ps_identifyer = "psg_eps_file*%i" % (
                self.document.new_embed_number(), )
            # If the EPS file is supposed to live at document level,
            # we create a file resource in its prolog.

            # The mechanism was written and excellently explained by
            # Thomas D. Greer at http://www.tgreer.com/eps_vdp2.html .
            resource = ResourceSection("file", self.resource_identifyer)
            self.document.add_resource(resource)

            resource.print("/%sImageData currentfile" % ps_identifyer)
            resource.print("<< /Filter /SubFileDecode")
            resource.print("   /DecodeParms << /EODCount")
            resource.print("       0 /EODString (***EOD***) >>")
            resource.print(">> /ReusableStreamDecode filter")
            resource.append(self.subfile)
            resource.print("***EOD***")
            resource.print("def")
            resource.print()
            resource.print("/%s " % ps_identifyer)
            resource.print("<< /FormType 1")
            resource.print("   /BBox [%f %f %f %f]" % self.as_tuple())
            resource.print("   /Matrix [ 1 0 0 1 0 0]")
            resource.print("   /PaintProc")
            resource.print("   { pop")
            resource.print("       /ostate save def")
            resource.print("         /showpage {} def")
            resource.print("         /setpagedevice /pop load def")
            resource.print("         %sImageData 0 setfileposition" % (
                                                          ps_identifyer) )
            resource.print("            %sImageData cvx exec" % (
                                                          ps_identifyer) )
            resource.print("       ostate restore")
            resource.print("   } bind")
            resource.print(">> def")

            # Store the ps code to use the eps file in self
            self.print("%s execform" % ps_identifyer)
        else:
            self.document.add_resource(procsets.embed_eps)
            self.print("psg_begin_epsf")
            self.append(Comment("BeginDocument", self.resource_identifyer))
            self.append(self.subfile)
            self.print()
            self.append(Comment("EndDocument"))
            self.print("psg_end_epsf")


    def fit(self, canvas):
        """
        Fit this image into `canvas` so that it will set at (0,0) filling
        as much of the canvas as possible.  Return the size of the
        scaled image as a pair of floats (in PostScript units).
        """
        w = canvas.w
        factor = w / self.w
        h = self.h * factor

        if h > canvas.h:
            h = canvas.h
            factor = h / self.h
            w = self.w * factor

        canvas.print("gsave % fit() of", self.comment)
        canvas.print(factor, factor, "scale", "% fit() of ", self.comment)
        canvas.append(self)
        canvas.print("grestore % fit() of", self.comment)

        return (w, h)

class EPSImage(EPSBox):
    """
    Include a EPS complient PostScript document into the target
    PostScript file.
    """
    def __init__(self, fp, document_level=True,
                 border=False, clip=False, comment=""):
        """
        @param fp: File pointer opened for reading of the EPS file to be
           included
        @param document_level: Boolean indicating whether the EPS file shall
           be part of the document prolog and be referenced several times from
           within the document, or if it shall be included where it is used
           for a single usage.
        """
        fp = eps_file_without_preview(fp)
        bb = get_eps_bb(fp)
        fp.seek(0)

        super().__init__(fp, bb, document_level, border, clip, comment)

class RasterImage(EPSBox):
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

    def __init__(self, pil_image, document_level=True,
                 border=False, clip=False, comment=""):
        """
        @param pil_image: Instance of PIL's image class
        @param document_level: Boolean indicating whether the EPS file shall
           be part of the document prolog and be referenced several times from
           within the document or if it shall be included where it is used
           for a single usage.
        """
        width, height = pil_image.size
        bb = Rectangle(0, 0, width, height)

        # FIXME: This should be dealt with more intelligently.
        if pil_image.mode == "1":
            pil_image = pil_image.convert("L")

        super().__init__(self.raster_image_buffer(pil_image),
                         bb, document_level, border, clip, comment)

class LineBox(Box):
    """
    A canvas for a single line of text to be rendered on.
    """
    def __init__(self, textbox, top, height):
        super().__init__(0, top-height,
                         textbox.line_width_at(top, height), height,
                         border=False)
        self.top = top
        self.textbox = textbox

    @property
    def w(self):
        return self._w

    @w.setter
    def w(self, w):
        self._w = w

    @property
    def h(self):
        return self._h

    @h.setter
    def h(self, h):
        self._h = h

    @property
    def y(self):
        return self.top - self.h

    def on_parent_set(self):
        """
        When added to the textbox, the line is rendered into the the
        body. (It is a boxes.BoxBuffer!)
        """
        self.print(0, self.y-self.h, "moveto")



class TextBoxTooSmall(Exception):
    pass

class TextBoxesExhausted(Exception):
    pass

class TextBox(Canvas):
    """
    A (rectangular) canvas for multiple lines of text (potentially
    of different heights) may be rendered.

    The TextBox maintains a cursor, starting at its top, counting it
    down to 0 with every LineBox append()ed to it. It provides several
    functions to construct LineBoxes that are connected to it but not
    automatically appended.

    You may only append() LineBox objects to a TextBox. However, a
    textbox is a BoxBuffer which has a head and a tail.
    """
    def __init__(self, x, y, w, h, border=False, clip=False, comment=""):
        super().__init__(x, y, w, h, border, clip, comment)

        # The cursor is pointing at the upper edge of the box.
        # With each line append()ed, it is advanced downward.
        self._cursor = h

    @property
    def cursor(self):
        return self._cursor

    def advance_cursor(self, amount):
        if self.cursor - amount < 0:
            raise TextBoxTooSmall()
        else:
            self._cursor -= amount

    def write(self, *lines):
        """
        Only LineBoxes may be added to a TextBox. Adding lines
        will advance the cursor downward. No bounds check for the
        bottom is performed.
        """
        for line in lines:
            assert isinstance(line, LineBox), TypeError

            super().write(line)
            self._cursor -= line.h

    def typeset(self, lines):
        self.write(*lines)

    def pop(self):
        """
        Remove and return the last line.
        """
        return self._things.pop()

    @property
    def lines(self):
        return self._things

    def __len__(self):
        return len(self._things)

    @property
    def empty(self):
        return len(self._things) == 0

    def line_width_at(self, y, height):
        """
        Return the widht of a potential LineBox at `y` with
        `height`. If such a line will not fit the TextBox, return
        None. Should the cursor already have advanced past `y`,
        a ValueError will be raised.
        """
        if y > self._cursor:
            # Asking for a line above the cursor would overlap lines
            # in this Textbox (or exceed the upper bound of the box).
            raise ValueError("y out of range, above cursor.")

        if y - height < 0:
            return None
        else:
            # Since this is a rectangular box we always return the box’s width.
            return self._calculate_width_at(y, height)

    def _calculate_width_at(self, y, height):
        """
        Calculate the width at a height, after all the checks are done.
        """
        return self.w

    @property
    def room_left(self):
        """
        How much vertical room is left in this box?
        """
        return self._cursor

    @property
    def has_room(self, height):
        """
        Does this textbox have room for a line of `height`?
        """
        return (self._cursor >= height)

    def clear(self):
        self._things = []
        self._font_instance = None
        self._cursor = self.h
