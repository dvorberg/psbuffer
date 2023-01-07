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
This module defines and implements a variaty of text and/or paragraph
backgrounds.
"""

class background(object):
    """
    Abstract base class.
    """
    def __repr__(self):
        return "<%s background>" % self.__class__.__name__

class none(background):
    def __nonzero__(self):
        return False

    def __repr__(self):
        return "<no background>"

transparent = none        

class color(background):
    """
    Fill the background with the specified color.
    """
    def __init__(self, color):
        self._color = color

    @property
    def color(self):
        return self._color

