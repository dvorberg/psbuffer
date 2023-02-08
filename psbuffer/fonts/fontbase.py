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

import functools, unicodedata, warnings
from ..dsc import DSCBuffer, PageBase, ResourceSection
from .encoding_tables import codepoint_to_glyph_name

class FontResourceSection(ResourceSection):
    def __init__(self, font):
        super().__init__("font", font.ps_name)
        self.font = font

class Font(object):
    """
    Abstract base class for fonts.
    """
    def __init__(self, ps_name, full_name, family_name,
                 weight, italic, fixed_width, metrics):
        """
        All these params become instance variables.

        @param ps_name: PostscriptIdentifyer for this font
        @param full_name: Human readable name
        @param family_name: The font family's name
        @param weight: Font weight as a string (Regular, Bold, SemiBold etc)
        @param italic: Boolean indicating whether this font is italic
        @param fixed_width: Boolean indicating whether this font has a fixed
           character width
        @param matrics: An instance of FontMetrics containing the font
           metrics. This is a dict mapping unicode code points to GlyphMetric
           obects.
        """
        self.ps_name = ps_name
        self.full_name = full_name
        self.family_name = family_name
        self.weight = weight
        self.italic = italic
        self.fixed_width = fixed_width

        self.metrics = metrics

    def has_char(self, codepoint):
        return codepoint in self.metrics

    def make_wrapper_for(self, page:PageBase):
        return FontWrapper(self, page)

    @property
    def resource_section(self):
        raise NotImplemented()

class GlyphMetric:
    def __init__(self, char_code, width, ps_name, bounding_box):
        """
        @param char_code: Character code in font encoding
        @param width: Character width in 1/1000th unit
        @param ps_name: PostScript character name. May be None.
        @param bounding_box: Charachter bounding box in 1/1000th unit
        """
        self.char_code = char_code
        self.ps_name = ps_name
        self.width = width
        self.bounding_box = bounding_box

    def __repr__(self):
        return "<%s code=%i width=%f ps_name=%s>" % (
            self.__class__.__name__, self.font_character_code,
            self.width, self.ps_name, )


class FontMetrics(dict):
    """
    Base class for font metric calculaions. Metrics objects are
    dict that map unicode codepoints (integers) to glyph_metric
    objects. The class provides a special mechanism for accessing
    calculated attributes, see __getattr__() below.

    @ivar kerning_pairs: Dict object mapping tuples of integer (unicode
      codes) to floats (kerning value for that pair).
    """
    def __init__(self):
        self.kerning_pairs = {}
        self.kerning_pairs.setdefault(0.0)

    @property
    def codepoints(self):
        """
        Return a list of available character codes.
        """
        return list(self.keys())

    def charwidth(self, codepoint, font_size):
        return self.get(codepoint, self[32]).width * font_size / 1000.0

    def stringwidth(self, s, font_size, kerning=True, char_spacing=0.0):
        """
        Return the width of s when rendered in the current font in
        regular PostScript units. The boolean parameter kerning
        indicates whether the font’s pair-wise kerning information
        will be taken into account, if available. The char_spacing
        parameter is in regular PostScript units, too.
        """
        s = [ ord(c) for c in s ]

        if len(s) == 1:
            return self.charwidth(s[0], font_size)
        else:
            space_metric = self[32]
            width = sum([self.get(char, space_metric).width * font_size
                         for char in s])

            if kerning:
                for char, next in zip(s[:-1], s[1:]):
                    kerning = self.kerning_pairs.get(
                        (char, next,), 0.0 )
                    width += kerning * font_size

            if char_spacing > 0.0:
                width += (len(s) - 1) * char_spacing * 1000.0

            return width / 1000.0

class SetupLinesForFont(object):
    def __init__(self, font_wrapper):
        self.font_wrapper = font_wrapper

    def write_to(self, fp):
        ps_name = self.font_wrapper.ps_name.encode("ascii")

        fp.write(b"%% Setup lines for %s\n" % ps_name)
        fp.write(self.setup_lines())
        fp.write(b"%% End of setup lines for %s\n" % ps_name)

    def setup_lines(self):
        """
        Return the PostScript code that goes into the page's setup
        section.
        """
        font = self.font_wrapper.font

        # Turn the mapping around.
        mapping = dict([ (pscode, codepoint,)
                         for (codepoint, pscode,)
                         in self.font_wrapper.mapping.items() ])

        nodefs = 0
        encoding_vector = []

        for pscode in range(256):
            if pscode in mapping:
                uniord = mapping[pscode]
                if font.has_char(uniord):
                    if nodefs == 1:
                        encoding_vector.append("/.nodef")
                        nodefs = 0
                    elif nodefs > 1:
                        encoding_vector.append("%i{/.nodef}repeat" % nodefs)
                        nodefs = 0

                    glyph_metric = font.metrics[uniord]
                    ps = "/%s" % glyph_metric.ps_name
                else:
                    ps = "/uni%0000X" % mapping[a]

                encoding_vector.append("%s %% key=%i %s" % (
                        ps, pscode, unicodedata.name(chr(uniord)),))
            else:
                nodefs += 1

        if nodefs != 0:
            encoding_vector.append("%i{/.nodef}repeat" % nodefs)

        tpl = ( self.font_wrapper.ps_name,
                "\n  ".join(encoding_vector),
                self.font_wrapper.font.ps_name, )
        setup = "/%s [\n  %s\n]\n /%s findfont " % tpl + \
            "psg_reencode 2 copy definefont pop def\n"

        return setup.encode("ascii")


class FontWrapper(object):
    """
    The FontWrapper binds it all together. It provides the relevant
    methods of Font, FontMetric and has functionality to create PostScript
    code for the font instance bound to a specific page.

    self.mappging: Maps unciode code points to 8-bit PostScript codes
       used to encode corresponding glyphs.
    """
    def __init__(self, font:Font, page:PageBase):
        self.font = font
        self.metrics = font.metrics
        self.page = page

        self.mapping = {}
        for a in range(32,127):
            self.mapping[a] = a
        self.next = 127

        page.setup.append(SetupLinesForFont(self))

    def has_char(self, codepoint):
        return codepoint in self.metrics

    @property
    def codepoints(self):
        return self.metrics.codepoints

    def charwidth(self, codepoint, font_size):
        return self.metrics.charwidth(codepoint, font_size)

    def stringwidth(self, s, font_size, kerning=True, char_spacing=0.0):
        return self.metrics.stringwidth(s, font_size, kerning, char_spacing)

    @functools.cached_property
    def ordinal(self):
        return self.page.ordinal

    def register_chars(self, chars:str, ignore_missing=True):
        for char in chars:
            char = ord(char)

            if not self.font.has_char(char):
                if ignore_missing:
                    if char in codepoint_to_glyph_name:
                        tpl = ( self.font.ps_name,
                                codepoint_to_glyph_name[char], )
                    else:
                        tpl = ( self.font.ps_name, "#%i" % char, )

                    msg = "%s does not contain needed glyph %s" % tpl
                    warnings.warn(msg)
                    char = 32 # space
                else:
                    tpl = ( char, repr(unichr(char)), )
                    msg = "No glyph for unicode char %i (%s)" % tpl
                    raise KeyError(msg)

            if not char in self.mapping:
                self.next += 1

                if self.next > 254:
                    # Use the first 31 chars (except \000) last.
                    self.next = -1
                    for b in range(1, 32):
                        if not b in self.mapping:
                            self.next = b

                    if next == -1:
                        # If these are exhausted as well, replace
                        # the char by the space character.
                        warning.warn(f"No 8-bit codes left in {self.ps_name} "
                                     f"(page no. {self.page.ordinal})")
                        next = 32
                    else:
                        next = self.next
                else:
                    next = self.next

                self.mapping[char] = next

    def postscript_representation(self, us):
        """
        Return a regular 8bit string in this particular encoding
        representing unicode string 'us'. This function will register
        all characters in us with this page.
        """
        self.register_chars(us)
        ret = bytearray()

        for char in us:
            codepoint = ord(char)
            byte = self.mapping.get(codepoint, None)

            if byte is None:
                ps = [32,] # Space
            else:
                if byte < 32 or byte > 240 or byte in (40,41,92,):
                    ps = b"\%03o" % byte
                else:
                    ps = [byte,]

            ret.extend(ps)

        return ret

    @property
    def ps_name(self):
        """
        Return the name of the re-encoded font for this page.
        """
        return "%s*%i" % ( self.font.ps_name, self.ordinal, )
