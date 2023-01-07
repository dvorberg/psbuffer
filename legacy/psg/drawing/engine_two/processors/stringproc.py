#!/usr/bin/python
# -*- coding: utf-8; mode: python; ispell-local-dictionary: "english"; -*-

##  This file is part of psg, PostScript Generator.
##
##  Copyright 2014 by Diedrich Vorberg <diedrich@tux4web.de>
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
This module provides a number of functions to split input text
into engine_two.elements objects. Simple string functions are used to
determin word boundaries.
"""
import types
from string import *

from .. import elements

def words(text, style=None):
    """
    Yields elements.word objects, one for each of the
    white-space separated words in `text`. 
    """
    if type(text) != types.UnicodeType:
        text = unicode(str(text))

    words = splitfields(text)
    
    if len(words) == 0:
        words = [u'\u200b',] # ZERO WIDTH SPACE
        
    return map(lambda word: elements.word(elements.syllable(word),
                                          style=style),
               words)

def paragraph(text, style=None):
    """
    Return an elements.paragraph object containing the white-space
    separated words in text.
    """
    return elements.paragraph(words(text), style=style)
    
