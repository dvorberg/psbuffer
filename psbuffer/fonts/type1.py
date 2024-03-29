#!/usr/bin/python

##  This file is part of psg, PostScript Generator.
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

"""
This module contains code to handle PostScript Type1 fonts.
"""

import re

from ..measure import Rectangle
from ..utils import pfb2pfa_Buffer
from ..base import FileAsBuffer
from .. import procsets

from .fontbase import Font, GlyphMetric, FontMetrics, FontResourceSection
from .encoding_tables import encoding_tables, glyph_name_to_codepoint
from .afm_parser import parse_afm

class Type1(Font):
    """
    A Type1 font loaded from an outline and a metrics file.

    The outline file (in pfa/b format) will be converted to pfa and
    included in the output file entirely.
    """
    def __init__(self, outline_file, metrics_file):
        """
        @param outline_file: File pointer of a .pfa/b file.
        @param metrics_file: File pointer of the corresponding .afm file
        """
        self.outline_file = outline_file

        metrics = AFMMetrics(metrics_file)

        super().__init__(metrics.ps_name,
                         metrics.full_name,
                         metrics.family_name,
                         metrics.weight,
                         metrics.italic,
                         metrics.fixed_width,
                         metrics)

    def add_to(self, document):
        document.add_resource(procsets.font_utils)
        document.header.supplied_fonts.append(self.ps_name)
        document.add_resource(Type1ResourceSection(self))


class ResidentType1(Font):
    """
    A Type1 font available to the Postscript interpreter, for which a
    metrics file is provided.

    The most common use is probably placing the outline file in
    Ghostscript’s include path and adding a line to a Fontmap file.
    Fontmap files map ps_names (as Postscript identifyers) to
    filenames (as Postscript string literals). Each pair ends with a
    semicolon like so:

        /CMUSansSerif-Medium (CMUSansSerif-Medium.pfb);

    You may use any font format Ghostscript understands for the font,
    but the metrics file must be in AFM format. Fontforge knows how to
    create these and does so when writing Type 1 font files.
    """
    def __init__(self, metrics_file, ps_name=None):
        """
        `metrics_file`: File pointer of a .afm file
        The `ps_name` will be used when referring to the font,
        otherwise it is loaded from the afm file.
        """
        metrics = AFMMetrics(metrics_file)

        super().__init__(ps_name or metrics.ps_name,
                         metrics.full_name,
                         metrics.family_name,
                         metrics.weight,
                         metrics.italic,
                         metrics.fixed_width,
                         metrics)

    def add_to(self, document):
        document.add_resource(procsets.font_utils)
        document.add_needed_resource("font", self.ps_name)


class Type1ResourceSection(FontResourceSection):
    def __init__(self, font):
        super().__init__(font)

        if hasattr(font.outline_file, "encoding"):
            fp = font.outline_file.buffer
        else:
            fp = font.outline_file

        fp.seek(0)

        first_line = fp.read(30)
        first_byte = first_line[0]
        fp.seek(0)

        if first_byte == 128: # pfb
            self.append(pfb2pfa_Buffer(fp))
        else:
            if not first_line.startswith(b"%!PS-AdobeFont"):
                raise NotImplementedError("Not a pfa/b file!")
            else:
                self.append(FileAsBuffer(fp))


class global_info(property):
    """
    Property class for properties that can be retrieved directly from
    the parser data.
    """
    def __init__(self, keyword):
        self.keyword = keyword

    def __get__(self, metrics, owner="dummy"):
        return metrics.FontMetrics.get(self.keyword, None)

class AFMMetrics(FontMetrics):
    gs_uni_re = re.compile("uni([A-Fa-f0-9]+).*")

    def __init__(self, fp):
        """
        @param fp: File pointer of the AFM file opened for reading.
        @raises KeyError: if the font's encoding is not known.
        """
        super().__init__()

        self.FontMetrics = parse_afm(fp)

        try:
            encoding_table = encoding_tables.get(self.encoding_scheme)
        except KeyError:
            raise KeyError("Unknown font encoding: %s" % \
                                                repr(self.encoding_scheme))

        # Create a glyph_metric object for every glyph and put it into self
        # indexed by its unicode code.
        char_metrics = self.FontMetrics["Direction"][0]["CharMetrics"]
        for char_code, info in char_metrics.iteritems():
            glyph_name = info.get("N", None)

            uni_match = self.gs_uni_re.match(glyph_name)

            if glyph_name is None:
                unicode_char_code = encoding_table[char_code]
            elif glyph_name == ".notdef":
                continue
            elif uni_match is not None:
                # This may be a Ghostscript specific convention. No word
                # about this in the standard document.
                unicode_char_code = int(uni_match.groups()[0], 16)
            else:
                try:
                    unicode_char_code = glyph_name_to_codepoint[glyph_name]
                except KeyError:
                    continue

            bb = Rectangle.from_coordinates(*info["B"])
            self[unicode_char_code] = GlyphMetric(
                char_code, info["W0X"] / 1000.0, glyph_name, bb)

        # Create kerning pair index
        try:
            kern_pairs = self.FontMetrics["KernData"]["KernPairs"]

            for pair, info in kern_pairs.iteritems():
                a, b = pair
                key, info0, info1 = info

                if key == "KPH":
                    a = encoding_table[a]
                    b = encoding_table[b]
                else:
                    a = glyph_name_to_codepoint[a]
                    b = glyph_name_to_codepoint[b]

                kerning = info0

                self.kerning_pairs[ ( a, b, ) ] = kerning / 1000.0

        except KeyError:
            pass

    ps_name = global_info("FontName")
    full_name = global_info("FullName")
    family_name = global_info("FamilyName")
    weight = global_info("Weight")
    character_set = global_info("CharacterSet")
    encoding_scheme = global_info("EncodingScheme")
    fontbbox = global_info("FontBBox")
    ascender = global_info("Ascender")
    descender = global_info("Descender")

    @property
    def italic(self):
        if self.FontMetrics.get("ItalicAngle", 0) == 0:
            return False
        else:
            return True

    @property
    def fixed_width(self):
        Direction = self.FontMetrics["Direction"][0]
        if Direction is None:
            return None
        else:
            return Direction.get("IsFixedPitch", False)

    @property
    def character_codes(self):
        """
        Return a list of available character codes in font encoding.
        """
        cm = self.FontMetrics["Direction"][0]["CharMetrics"]
        return cm.keys()

    @property
    def font_bounding_box(self):
        """
        Return the font bounding box as a bounding_box object in regular
        PostScript units.
        """
        numbers = self.fontbbox
        numbers = map(lambda n: n / 1000.0, numbers)
        return Rectangle.from_coordinates(*numbers)

if __name__ == "__main__":
    import sys

    fp = open(sys.argv[1])
    metrics = AFMMetrics(fp)

    print("PS Name     ", metrics.ps_name)
    print("Full Name   ", metrics.full_name)
    print("Family Name ", metrics.family_name)
    print("Weight      ", metrics.weight)
    print("Italic?     ", metrics.italic)
    print("Fixed width?", metrics.fixed_width)
    print()
    s = "Diedrich Vorberg"
    for c in s:
        print(c, metrics.charwidth(ord(c), 10))
    print()
    print(metrics.stringwidth(s, 10, kerning=False), "kerning=False")
    print(metrics.stringwidth(s, 10, kerning=True), "kerning=True")
