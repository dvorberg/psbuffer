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
This module contains code to handle PostScript Type1 fonts.
"""

import os.path as op
from types import *

from font import font
from afm_metrics import afm_metrics

class type1(font):
    """
    Model a PostScript Type1 font.

    @ivar charmap: Dictionary with unicode character codes as keys and
      the coresponding char (glyph) code as values.
    """
    def __init__(self, main_font_file, afm_file):
        """
        @param main_font: Filepointer of a .pfa/b file. This may be
           None for resident fonts.
        @param afm_file: File pointer of the corresponding .afm file
        """
        if type(main_font_file) == StringType:
            main_font_file = open(main_font_file)

        if type(afm_file) == StringType:
            afm_file = open(afm_file)
        
        self._main_font_file = main_font_file
        self._afm_file = afm_file
        
        metrics = afm_metrics(afm_file)

        font.__init__(self,
                      metrics.ps_name,
                      metrics.full_name,
                      metrics.family_name,
                      metrics.weight,
                      metrics.italic,
                      metrics.fixed_width,
                      metrics)

    def has_char(self, unicode_char_code):
        return self.metrics.has_key(unicode_char_code)

    def main_font_file(self):
        return self._main_font_file

    def afm_file(self):
        return self._afm_file
        
class lazy_loader(type1):
    """
    A wrapper class that can be used like a function. Using
    t4.psg.fonts.computer_modern.sans_serif().
    """
    def __init__(self, filename):
        self.__font_filename = filename
        self.__font = None

    def here(self):
        """
        Return the directory path where to search for `filename`.
        """
        raise NotImplemented()
        
    def __call__(self):
        if self.__font is None:
            shapes = op.join(self.here(), self.__font_filename + ".pfb")
            metric = op.join(self.here(), self.__font_filename + ".afm")
        
            self.__font = type1(shapes, metric)
            
        return self.__font

    def __getattr__(self, name):
        # This will load the font when used for the first time.
        return getattr(self(), name)

