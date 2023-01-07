#!/usr/bin/python
# -*- coding: utf-8; mode: python; ispell-local-dictionary: "english"; -*-

##  This file is part of psg, PostScript Generator.
##
##  Copyright 2006–15 by Diedrich Vorberg <diedrich@tux4web.de>
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

import re, subfile, struct
from measure import bounding_box

hires_bbre = re.compile(
    r"%%HiResBoundingBox: (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) "
    r"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)")
bbre = re.compile(r"%%BoundingBox: (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) "
                  r"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)")
def get_eps_bb(fp_or_eps):
    """
    Provided EPS Source code, this function will return a pair of
    floats in PostScript units. If a %%HiResBoundingBox can’t be
    found, raise ValueError. The file pointer will be reset to the
    current position.
    """
    if hasattr(fp_or_eps, "read"):
        here = fp_or_eps.tell()
        eps = fp_or_eps.read(1024)
        fp_or_eps.seek(here)
    else:
        eps = remove_eps_preview(fp_or_eps[:1024])
        
    match = hires_bbre.search(eps)
    if match is None:
        match = bbre.search(eps)
        
    if match is not None:
        left, bottom, right, top = map(float, match.groups())
        return bounding_box(left, bottom, right, top)
    else:        
        raise ValueError("Can’t find bounding box in EPS.")

def get_eps_size(fp_or_eps):
    bb = get_eps_bb(fp_or_eps)
    return bb.width(), bb.height(),
        
def remove_eps_preview(epsdata):
    """
    Return the part of “epsdata” that contains the PostScript language
    code section.

    C.f. Encapsulated PostScript File Format Specification
         Adobe Developer Support, Version 3.0, 1 May 1992, pp. 24f.
    """
    if epsdata.startswith("%!PS-Adobe-"):
        return epsdata
    else:
        header = epsdata[:12]
        marker, pspos, pslength = struct.unpack("<III", header)
        # The manual says the marker must be c5d03d6d. That seems to be
        # little-endian or something. If I use this, plus “<” in unpack,
        # this works.
        if marker != 0xc6d3d0c5:
            raise IOError("Can’t identify image format.")
        return epsdata[pspos:pspos+pslength]

def eps_file_without_preview(epsfp):
    """
    Return a subfile.subfile of epsfp, if it is an eps file that as a
    preview header. The file pointer will be reset to the current
    position.
    """
    here = epsfp.tell()
    header = epsfp.read(50)    
    epsfp.seek(here)
    
    if header.startswith("%!PS-Adobe-"):
        # This EPS file does not have a header.
        return epsfp
    else:        
        marker, pspos, pslength = struct.unpack("<III", header[:12])
        return subfile.subfile(epsfp, pspos, pslength)
        
    
