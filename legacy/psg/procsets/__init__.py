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
Procsets are predefined PostScript programs that are put into a
document's header if psg needs them. They are read from .ps files in
the procset module's directory.
"""
import sys, re, os, os.path
from string import *
from glob import glob

from t4.psg.document.dsc import dsc_resource, \
    resource_section as dsc_section

directory = os.path.dirname(__file__)
files = glob("%s/*.ps" % directory)

revision_re = re.compile(r"\$\s*Revision:\s*(\d+)\.(\d+)\s*\$")

for file_name in files:
    ps = open(file_name).read()    
    parts = split(os.path.basename(file_name), ".") # split of the .ps
    var_name = parts[0]
    
    result = revision_re.findall(ps)
    version = result[0]
    major, minor = version
    major, minor = int(major), int(minor)

    # create the procset name
    procset_name = "psg_%s %i %i" % ( var_name, major, minor, )

    # DSC procset
    section = dsc_section(info="procset %s" % procset_name)
    print >> section, ps
    globals()["dsc_%s" % var_name] = dsc_resource(type="procset",
                                                  name=procset_name,
                                                  section=section,
                                                  setup_lines=None)
