#!/usr/bin/python

##  This file is part of psg, PostScript Generator.
##
##  Copyright 2006-23 by Diedrich Vorberg <diedrich@tux4web.de>
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

from . import glyph_name_to_codepoint
from ..base import Font, GlyphMetric, FontMetrics

from .encoding_tables import encoding_tables
from .afm_parser import parse_afm

class global_info(property):
    """
    Property class for properties that can be retrieved directly from
    the parser data.
    """
    def __init__(self, keyword):
        self.keyword = keyword

    def __get__(self, metrics, owner="dummy"):
        return metrics.FontMetrics.get(self.keyword, None)

class Type1(Font):
    """
    Model a PostScript Type1 font.

    @ivar charmap: Dictionary with unicode character codes as keys and
      the coresponding char (glyph) code as values.
    """
    def __init__(self, outline_file, metrics_file):
        """
        @param main_font: Filepointer of a .pfa/b file. This may be
           None for resident fonts.
        @param afm_file: File pointer of the corresponding .afm file
        """
        self.outline_file = outline_file
        self.metrics_file = metrics_file

        metrics = AFMMetrics(metrics_file)

        font.__init__(self,
                      metrics.ps_name,
                      metrics.full_name,
                      metrics.family_name,
                      metrics.weight,
                      metrics.italic,
                      metrics.fixed_width,
                      metrics)

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

            bb = bounding_box.from_tuple(info["B"])
            self[unicode_char_code] = GlyphMetric(char_code,
                                                  info["W0X"],
                                                  glyph_name,
                                                  bb)

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

                self.kerning_pairs[ ( a, b, ) ] = kerning
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
        return bounding_box.from_tuple(numbers)

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
