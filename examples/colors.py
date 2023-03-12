#!/usr/bin/env python

##  This file is part of psg, PostScript Generator.
##
##  Copyright 2023 by Diedrich Vorberg <diedrich@tux4web.de>
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


######################################################################
# When I grow up, I’ll be a unit test!

from io import BytesIO

from psbuffer.base import PSBuffer
from psbuffer import colors

def main():
    b = PSBuffer()

    for a in ("white", "black", "red", "green", "blue"):
        b.print(getattr(colors, a), f"% {a}")

    b.print()
    b.print(colors.WebColor("#FFBE33"), b'% WebColor("#FFBE33"))')

    fp = BytesIO()
    b.write_to(fp)

    print(fp.getvalue().decode("ascii"))

main()
