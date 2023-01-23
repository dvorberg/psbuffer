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




PAPERSIZES = {
    # This dict is copied over from the pyscript project.

    # Page sizes defined by Adobe documentation
    "11x17": (792, 1224),
    # a3 see below
    # a4 see below
    # a4small should be a4 with an ImagingBBox of [25 25 570 817].
    # b5 see below
    "ledger": (1224, 792), # 11x17 landscape
    "legal": (612, 1008),
    "letter": (612, 792),
    # lettersmall should be letter with an ImagingBBox of [25 25 587 767].
    # note should be letter (or some other size) with the ImagingBBox
    # shrunk by 25 units on all 4 sides.

    # ISO standard paper sizes
    "a0": (2380, 3368),
    "a1": (1684, 2380),
    "a2": (1190, 1684),
    "a3": (842, 1190),
    "a4": (595, 842),
    "a5": (421, 595),
    "a6": (297, 421),
    "a7": (210, 297),
    "a8": (148, 210),
    "a9": (105, 148),
    "a10": (74, 105),

    # ISO and JIS B sizes are different....
    # first ISO
    "b0": (2836, 4008),
    "b1": (2004, 2836),
    "b2": (1418, 2004),
    "b3": (1002, 1418),
    "b4": (709, 1002),
    "b5": (501, 709),
    "b6": (354, 501),
    "jisb0": (2916, 4128),
    "jisb1": (2064, 2916),
    "jisb2": (1458, 2064),
    "jisb3": (1032, 1458),
    "jisb4": (729, 1032),
    "jisb5": (516, 729),
    "jisb6": (363, 516),
    "c0": (2600, 3677),
    "c1": (1837, 2600),
    "c2": (1298, 1837),
    "c3": (918, 1298),
    "c4": (649, 918),
    "c5": (459, 649),
    "c6": (323, 459),

    # U.S. CAD standard paper sizes
    "arche": (2592, 3456),
    "archd": (1728, 2592),
    "archc": (1296, 1728),
    "archb": (864, 1296),
    "archa": (648, 864),

    # Other paper sizes
    "flsa": (612, 936), # U.S. foolscap
    "flse": (612, 936), # European foolscap
    "halfletter": (396, 612),

    # Screen size (NB this is 2mm too wide for A4):
    "screen": (800, 600) }


def parse_size(size):
    if type(size) is str:
        name = size.lower()

        if name.endswith("landscape"):
            name = name.replace("landscape", "").strip()
            w, h = parse_size(name)
            return h, w
        elif name.endswith("portrait"):
            name = name.replace("portrait", "").strip()
            return parse_size(name)
        elif name in PAPERSIZES:
            w, h =  PAPERSIZES[name]
            return float(w), float(h)
        else:
            raise KeyError(name)

    elif type(size) is tuple:
        w, h = size
        return float(w), float(h),

    elif type(size) in ( float, int, ):
        return float(size), flost(size),
    else:
        raise TypeError()


# Units - convert everybody's units to PostScript Points

def pt(l):
    return l

def m(l):
     return l / 0.0254 * 72.0

def dm(l):
    return l / 0.254 * 72.0

def cm(l):
    return l / 2.54 * 72.0

def mm(l):
    return l / 25.4 * 72.0

def foot(l):
    return l * 12.0 * 72.0

feet = foot

def inch(l):
    return l * 72.0

def pc(l):
    return l / 6.0 * 72.0

pica = pc




class has_location(object):
    def __init__(self, x, y):
        self._x = x
        self._y = y

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

class has_dimensions(object):
    def __init__(self, w, h):
        self._w = w
        self._h = h

    @property
    def w(self):
        return self._w

    @property
    def h(self):
        return self._h

class Rectangle(has_location, has_dimensions):
    def __init__(self, x, y, w, h):
        has_location.__init__(self, x, y)
        has_dimensions.__init__(self, w, h)

    @classmethod
    def from_coordinates(cls, llx, lly, urx, ury):
        if llx > urx:
            (llx, urx) = (urx, llx)

        if lly > ury:
            (lly, ury) = (ury, lly)

        return cls(llx, lly, urx-llx, ury-lly)

    @property
    def llx(self):
        return self._x

    @property
    def urx(self):
        return self._x + self._w

    @property
    def lly(self):
        return self._y

    @property
    def ury(self):
        return self._y + self._h

    def as_tuple(self):
        return ( self.llx, self.lly, self.urx, self.ury, )
