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
This module defines psg speficic exceptions. 
"""

class PSGException(Exception): pass

class AFMParseError(PSGException):
    """
    ParseError in an AFM file
    """
    pass

class FontmapParseError(PSGException):
    """
    Parse error while reading Ghostscript's fontmap
    """
    pass

class FontNotFoundError(PSGException): pass
class FileNotFoundError(PSGException): pass
class IllegalFunctionCall(PSGException): pass
class DSCSyntaxError(PSGException): pass
class CommentMissing(PSGException): pass
class PFBError(PSGException): pass

class EndOfBox(PSGException): pass
class BoxTooSmall(PSGException): pass
class EndOfDocument(PSGException): pass
class IllegalPaperSize(PSGException): pass

