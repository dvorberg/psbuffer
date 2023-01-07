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
The model module contains classes used to represent the formating of a text.
"""

from t4.psg.fonts.font import font
from t4.psg.util import colors
from t4.cascading_style import cascading_style
from t4.cascading_style.constraints import accept_none, one_of, tuple_of, \
     isinstance as isinstance_constraint, unknown_property, conversion

import backgrounds, lists
from t4.psg.drawing.engine_two.hyphenator import hyphenator


class isfont(isinstance_constraint):
    """
    Make sure a style’s property is an instance of font.
    """
    def __init__(self):
        isinstance_constraint.__init__(self, font)


class font_family(cascading_style):
    """
    This defines a font family in a simple but usable way. A font
    family in our terms is a set of four font faces: regular, bold,
    italic and bold-italic. All faces default to the regular face
    which may not be None.    
    """
    __constraints__ = {
        "__default__": unknown_property(),
        "regular": isfont(),
        "italic": accept_none(isfont()),
        "bold": accept_none(isfont()),
        "bold-italic": accept_none(isfont()),
    }

    styles = { "normal", "italic" }
    weights = { "normal", "bold" }

    def __init__(self, styles={}, parent=None):
        self.bold = None
        self.italic = None
        self.bold_italic = None
        
        cascading_style.__init__(self, styles, parent)

        self.__by_spec = { "normal": { "normal": self.regular,
                                       "bold": self.bold, },
                           "italic": { "normal": self.italic,
                                       "bold": self.bold_italic, } }
    
    def __getitem__(self, name):
        """
        All four styles default to regular, which may not be None
        as specified in the constraints.
        """
        result = cascading_style.__getitem__(self, name)
        if result is None:
            return self.regular
        else:
            return result

    def getfont(self, style="normal", weight="normal"):
        """
        This is an additional accessor function that allows callers
        to query a font face by CSS’s style and weight keywords "normal",
        "italic" and "normal", "bold".
        """
        assert style in self.styles, ValueError(
            "Unknown font style: " + repr(style))
        assert weight in self.weights, ValueError(
            "Unknown font weight: " + repr(style))
        
        return self.__by_spec[style][weight]

    def __repr__(self):
        info = {}
        for key in self.__constraints__.keys():
            if key != "__default__":
                font = self.get(key, None)

                if font:
                    info[key] = font.full_name
                else:
                    info[key] = "%s not loaded" % key

        return repr(info)
    
    
class text_style(cascading_style):
    __constraints__ = {
        "__default__": unknown_property(),
        "font-family": isinstance_constraint(font_family),
        "font-size": conversion(float),
        "font-weight": one_of({"normal", "bold"}),
        "text-style": one_of({"normal", "italic"}),
        "line-height": conversion(float),
        "kerning": conversion(bool),
        "char-spacing": conversion(float),
        "color": isinstance_constraint(colors.color),
        "text-transform": accept_none(one_of({"lowercase", "uppercase"})),
        "hyphenator": accept_none(isinstance_constraint(hyphenator)), }

    def __init__(self, styles={}, parent=None, name=None):
        # Set default values.
        self.font_weight = "normal"
        self.text_style = "normal"
        self.kerning = True
        self.char_spacing = 0
        self.color = colors.black
        self.text_transform = None
        self.hyphenator = None

        cascading_style.__init__(self, styles, parent, name)
        

class box_style(cascading_style):    
    __constraints__ = {
        "__default__": unknown_property(),
        "margin": tuple_of(4, float),
        "padding": tuple_of(4, float),
        "background": isinstance_constraint(backgrounds.background), }

    def __init__(self, styles={}, parent=None, name=None):
        # Set default values.
        self.margin = (0, 0, 0, 0)
        self.padding = (0, 0, 0, 0)
        self.background = backgrounds.none()
        
        cascading_style.__init__(self, styles, parent, name)

    
class paragraph_style(cascading_style):
    __constraints__ = {
        "__default__": unknown_property(),
        "list-style": isinstance_constraint(lists.list_style),
        "text-align": one_of({"left", "right", "center", "justified"}) }

    def __init__(self, styles={}, parent=None, name=None):
        # Set default values.
        self.list_style = lists.none()
        self.text_align = "left"
        
        cascading_style.__init__(self, styles, parent, name)
        
class default_style(text_style, box_style, paragraph_style):
    """
    This style contains all the constraint definitions needed to
    render any psg.elements.* object in PostScript.
    """
    __constraints__ = {}

    def __init__(self, styles={}, parent=None, name=None):
        text_style.__init__(self, {}, None, None)
        box_style.__init__(self, {}, None, None)
        paragraph_style.__init__(self, {}, None, None)
        cascading_style.__init__(self, styles, parent, name)

class style(text_style, box_style, paragraph_style):
    """
    This style contains all the constraint definitions needed to
    render any psg.elements.* object in PostScript.
    """
    __constraints__ = {}

    def __init__(self, styles={}, parent=None, name=None):
        cascading_style.__init__(self, styles, parent, name)

