#!/usr/bin/python
# -*- coding: utf-8; -*-

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
 
"""

import sys, optparse

from t4.debug import log, debug

from t4.psg.util.wmf.postscript_reader import wmf2eps

def main(argv, doc):
    op = optparse.OptionParser(usage=doc)
    op.add_option("-o", None, dest="output_file", default="-",
                  help="Output file")
    log.add_option(op)
    debug.add_option(op)
    
    ( options, arguments, ) = op.parse_args()

    if len(arguments) != 1:
        op.error("Please specify a single wmf file on the command line.")
    else:
        infile_name = arguments[0]

    # Open the input file
    wmf_fp = open(infile_name, "r")

    # Open the output file
    if options.output_file == "-":
        eps_fp = sys.stdout
    else:
        eps_fp = open(options.output_file, "w")

    # Run the conversion process
    eps = wmf2eps(wmf_fp)

    if not (debug.verbose and options.output_file == "-"):
        eps.write_to(eps_fp)
    else:
        print >> debug, "DEBUG MODE ON, No output written!"
    
main(sys.argv, __doc__)


# Local variables:
# mode: python
# ispell-local-dictionary: "english"
# End:

