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
Procsets are predefined PostScript programs that are put into a
document's header if psg needs them. They are read from .ps files in
the procset module's directory.
"""

import re, os.path as op
from ..dsc import ResourceSection

revision_re = re.compile(br"\$\s*Revision:\s*(\d+)\.(\d+)\s*\$")

class ProcsetResourceSection(ResourceSection):
    def __init__(self, filename):
        filepath = op.join(op.dirname(__file__), filename)

        with open(filepath, "br") as fp:
            ps = fp.read()

        var_name, ext = op.splitext(filename)

        result = revision_re.findall(ps)
        version = result[0]
        major, minor = version
        major, minor = int(major), int(minor)

        # create the procset name
        procset_name = "psg_%s %i %i" % ( var_name, major, minor, )

        super().__init__("procset", f"psc_{var_name}", major, minor)
        self.write(ps)

embed_eps = ProcsetResourceSection("eps.ps")
font_utils = ProcsetResourceSection("font_utils.ps")
