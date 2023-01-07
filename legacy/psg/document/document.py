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
This module defines a base class for documents and a number of utility
classes.
"""

import sys, os, warnings, unicodedata
from string import *
from types import *

from t4.psg.exceptions import *
from t4.psg.util import *
from t4.psg.fonts.encoding_tables import unicode_to_glyph_name
from t4.web.title_to_id import asciify
from t4.debug import log

# A number of common Unicode characters not found in some fonts, that
# have rather obvious substitutions.

class resource:
    """
    A resource. Subclassed by dsc.resource.
    """
    def __init__(self, type, name, version):
        self.type = type
        self.name = name
        self.version = version

    def __equal__(self, other):
        """
        Two resources are condidered equal when their type and names
        (including version) match exactly.
        """
        if self.type == other.type and \
               strip(self.name) == strip(other.name):
            return True
        else:
            return False

    def __repr__(self):
        return "<resource %s %s vers: %s>" % ( self.type,
                                               self.name,
                                               self.version, )


class resource_set(ordered_set):
    def append(self, value):
        if not isinstance(value, resource):
            raise TypeError("A resource_set may only contain "
                            "resource instances, not " + repr(type(resource)))
        
        for index, a in enumerate(self):
            if a.type == "procset" and \
                   a.procset_name == value.procset_name and \
                   a.version <= value.version:
                self[index] = value
                return
            else:
                if value == a: return


        ordered_set.append(self, value)

    add = append

    def insert(self, *args):
        raise NotImplementedError()


    def union(self, other):
        ret = self.__class__()
        for a in self: ret.add(a)
        for a in other: ret.add(a)
        return ret
            

# The document class


class document:
    """
    Base class for all document classes. 
    """
    def __init__(self, title=None):
        if title is not None: self.title = title
        self._resources = resource_set()
        self._custom_colors = []
        self._required_resources = resource_set()
        self._page_counter = 0

    def add_resource(self, resource):
        self._resources.append(resource)

    def resources(self):
        return self._resources

    def add_required_resource(self, resource):
        self._required_resources.append(resource)

    def page(self, page_size="a4", label=None):
        """
        Return a page object suitable for and connected to this document.
        """
        return page(self, page_size, label)

    def _page__inc_page_counter(self):
        self._page_counter += 1

    def page_counter(self):
        return self._page_counter

    def output_file(self):
        """
        Return a file pointer in write mode for the pages to write
        their output to.
        """
        raise NotImplementedError()

    class custom_color:
        def __init__(self, _document, name, colspec):
            """
            @param name: String indicating the name of the color.
            @param colspec: Tuple of Float values either of length 1
                (Gray), 3 (RGB) or 4 (CMYK)
            """
            self._document = _document
            self.name = name

            try:
                colspec = map(float, colspec)
                if len(colspec) not in (1, 3, 4,):
                    raise ValueError
                else:
                    self.colspec = colspec                    
            except ValueError:
                raise ValueError("Color specification must be 1, 3 or 4 "
                                 "floats in a tuple.")


        def __str__(self):
            """
            Return a representation of this custom color in a
            document. The default implementation raises
            NotImplementedError()
            """
            raise NotImplementedError()
    
    def register_custom_color(self, name, colspec):
        """
        Pass the params to the constructor of the custom_color class
        above and return it. The custom colors will be kept treck of
        in the self._custom_colors list.
        
        @param name: String indicating the name of the color.
        @param colspec: Tuple of Float values either of length 1 (Gray),
            3 (RGB) or 4 (CMYK)
        """
        ret = self.custom_color(self, name, colspec)
        self._custom_colors.append(ret)
        return ret
    

class font_wrapper:
    """
    A font wrapper keeps track of which glyphs in a font have been
    used on a specific page. This information is then used to
    construct an encoding vector mapping 8bit values to glyphs. This
    imposes a limit: You can only use 255 distinct characters from any
    given font on a single page.
    """
    def __init__(self, page, ordinal, font, document_level):
        self.page = page
        self.ordinal = ordinal
        self.font = font

        self.mapping = {}
        for a in range(32,127):
            self.mapping[a] = a
        self.next = 127
        
    def register_chars(self, us, ignore_missing=True):
        if type(us) not in (UnicodeType, ListType,):
            raise TypeError("Please use unicode strings!")
        else:
            if type(us) == UnicodeType:
                chars = map(ord, us)
            else:
                chars = us

            for char in chars:
                if not self.font.has_char(char):
                    if ignore_missing:
                        if unicode_to_glyph_name.has_key(char):
                            tpl = ( self.font.ps_name,
                                    unicode_to_glyph_name[char], )
                        else:
                            tpl = ( self.font.ps_name, "#%i" % char, )

                        msg = "%s does not contain needed glyph %s" % tpl
                        if log.verbose:
                            warnings.warn(msg)
                        char = 32 # space
                    else:
                        tpl = ( char, repr(unichr(char)), )
                        msg = "No glyph for unicode char %i (%s)" % tpl
                        raise KeyError(msg)
                    
                if not self.mapping.has_key(char):
                    self.next += 1

                    if self.next > 254:
                        # Use the first 31 chars (except \000) last.
                        self.next = -1
                        for b in range(1, 32):
                            if not self.mapping.has_key(b):
                                self.next = b
                                
                        if next == -1:
                            # If these are exhausted as well, replace
                            # the char by the space character
                            next = 32
                        else:
                            next = self.next
                    else:
                        next = self.next

                    self.mapping[char] = next

    def postscript_representation(self, us):
        """
        Return a regular 8bit string in this particular encoding
        representing unicode string 'us'. 'us' may also be a list of
        integer unicode char numbers. This function will register all
        characters in us with this page.
        """
        if type(us) not in (UnicodeType, ListType):
            raise TypeError("Please use unicode strings!")
        else:
            if type(us) == ListType:
                chars = us
            else:
                chars = map(ord, us)
                
            self.register_chars(us)
            ret = []

            for char in chars:
                byte = self.mapping.get(char, None)

                if byte is None:
                    byte = " "
                else:
                    if byte < 32 or byte > 240 or byte in (40,41,92,):
                        byte = "\%03o" % byte
                    else:
                        byte = chr(byte)

                ret.append(byte)

            return join(ret, "")

    def setup_lines(self):
        """
        Return the PostScript code that goes into the page's setup
        section.
        """
        # turn the mapping around
        mapping = dict(map(lambda (char, glyph): (glyph, char),
                           self.mapping.iteritems()))

        nodefs = 0
        encoding_vector = []
        
        for a in range(256):
            if mapping.has_key(a):
                uniord = mapping[a]
                if self.font.metrics.has_key(uniord):
                    if nodefs == 1:
                        encoding_vector.append("/.nodef")
                        nodefs = 0
                    elif nodefs > 1:
                        encoding_vector.append("%i{/.nodef}repeat" % nodefs)
                        nodefs = 0

                    glyph_metric = self.font.metrics[uniord]
                    ps = "/%s" % glyph_metric.ps_name
                else:
                    ps = "/uni%0000X" % mapping[a]
                    
                encoding_vector.append("%s %% key=%i %s" % (
                        ps, a, lower(unicodedata.name(unichr(uniord))),))
            else:
                nodefs += 1

        if nodefs != 0:
            encoding_vector.append("%i{/.nodef}repeat" % nodefs)

        tpl = ( self.ps_name(),
                join(encoding_vector, "\n  "),
                self.font.ps_name, )
        return "/%s [\n  %s\n]\n /%s findfont " % tpl + \
               "psg_reencode 2 copy definefont pop def\n" 
        
    __str__ = setup_lines
                    
    def ps_name(self):
        """
        Return the name of the re-encoded font for this page.
        """
        return "%s*%i" % ( self.font.ps_name, self.ordinal, )
        
class page:
    """
    Model a page in a document.

    @ivar setup: File-like buffer to hold page initialisation code.
    @ivar _font_wrappers: Mapping of PostScript font names to font_wrapper
       instances for all the fonts registered with this page
    """
    
    def __init__(self, document, page_size="a4", label=None, ordinal=None):
        """
        Model a page in a document. A page knows about its resources,
        either on page or on document level.
        
        @param document: A psg.document instance.
        @param page_size: Either a string key for the PAPERSIZES dict
           above a pair of numerical values indicating the page's size
           in pt. Defaults to 'a4'. Note that opposed to the dict, the order
           of the tuple's elements is (width, height)
        @param label: A string label for this page (goes into the %%Page
           comment, defaults to a string representation of the page's ordinal,
           that is its one-based index within the document.)
        @raises KeyError: if the page_size is not known.
        """
        self.document = document
        
        if type(page_size) == TupleType:
            self._w, self._h = page_size
        else:
            self._w, self._h = PAPERSIZES[page_size]
            
        self._resources = resource_set()

        document.__inc_page_counter()

        if ordinal is None:
            self.ordinal = document.page_counter()
        else:
            self.ordinal = ordinal
            
        if label is None:
            self._label = str(self.ordinal)
        else:
            self._label = label

        self._number_of_fonts = 0
        self._font_wrappers = {}

    def w(self): return self._w
    def h(self): return self._h

    @property
    def label(self):
        return self._label
    
    def add_resource(self, resource, document_level=True):
        """
        Add a resource to this page or to this page's document (the default).
        """
        if document_level:
            self.document.add_resource(resource)
        else:
            self._resources.append(resource)

    def resources(self):
        return self._resources

    def canvas(self, margin=0, border=False, clip=False):
        """
        Return a canvas object for the whole page except a predefined
        set of margins.

        The margin parameter may be either:

          - an integer - all four margins the same
          - a pair - ( horizontal, vertical, )
          - a 4-tuple - ( left, top, right, bottom, )

        """

        if type(margin) == TupleType:
            if len(margin) == 2:
                h, v = margin
                margin = ( h, v, h, v, )
        else:
            m = float(margin)
            margin = ( m, m, m, m, )

        l, t, r, b = margin

        from t4.psg.drawing.box import canvas
        ret = canvas(self, l, b,
                     self.w() - r - l, self.h() - t - b,
                     border, clip)

        return ret

    def register_font(self, font, document_level=True):
        """
        This function will register a font with this page and return a
        font_wrapper object, see above. The boolean document_level
        parameter determines whether the font will be a document
        resource or a page resource.

        The page will keep track which fonts have been registered with
        it and cache wrapper objects. The document_level parameter is
        only meaningfull for the first call to register_font() with
        any given font. Fonts are keyed by their PostScript name, not
        the font objects.        
        """
        if not self._font_wrappers.has_key(font.ps_name):
            number_of_fonts = len(self._font_wrappers)
            wrapper = font_wrapper(self, number_of_fonts,
                                   font, document_level)
            self.pagesetup.append(wrapper)
            self._font_wrappers[font.ps_name] = wrapper

        return self._font_wrappers[font.ps_name]

