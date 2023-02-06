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

import os.path as op, re

glyph_name_to_codepoint = {}
codepoint_to_glyph_name = {}

#entry_re = re.compile(r"([A-Za-z0-9]+),([0-9a-f]+)")
with open(op.join(op.dirname(__file__), "glyph_name_to_unicode.csv")) as fp:
    for line_no, line in enumerate(fp.readlines()):
        line = line.rstrip()

        if not line or line[0] == "#":
            continue

        #match = entry_re.match(line)
        #if match is None:
        #    raise IOError(f"Illegal entry on line {line_no+1}: {repr(line)}")
        #else:
        #    glyph_name, codepoint = match.groups()
        #    codepoint = int(codepoint, 16)

        glyph_name, codepoint = line.split(",")
        codepoint = int(codepoint, 16)

        glyph_name_to_codepoint[glyph_name] = codepoint
        codepoint_to_glyph_name[codepoint] = glyph_name
