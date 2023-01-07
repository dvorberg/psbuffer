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

"""\
The `processors` module contains submodules, that convert representations of
rich text into an engine_two.model-tree that can be rendered.
"""

import sys, os, os.path as op
from t4.psg.document.dsc import dsc_document
from t4.psg.util import *
import t4.psg.drawing.box
    
def render_to_filename(richtext, outfile_name):
    """
    Mostly for testing purposes: Render a given richtext tree on A4 paper.
    """    
    margin = mm(18)

    outdoc = dsc_document("My first textbox example and testbed")

    def next_canvas():
        while True:
            page = outdoc.page()
            pcanvas = page.canvas(margin=margin)
            
            dist = margin / 2
            w = pcanvas.w() / 2 - dist
            h = pcanvas.h() / 2 - dist

            canvas = t4.psg.drawing.box.canvas(pcanvas,
                                               0, h + dist, w, h,
                                               border=True)
            pcanvas.append(canvas)        
            yield canvas

            canvas = t4.psg.drawing.box.canvas(pcanvas,
                                               w + dist, h + dist, w, h,
                                               border=True)
            pcanvas.append(canvas)        
            yield canvas

            canvas = t4.psg.drawing.box.canvas(pcanvas,
                                               0, 0, w, h,
                                               border=True)
            pcanvas.append(canvas)        
            yield canvas

            canvas = t4.psg.drawing.box.canvas(pcanvas,
                                               w + dist, 0, w, h,
                                               border=True)
            pcanvas.append(canvas)        
            yield canvas
        

    #import cProfile, pstats
    #pr = cProfile.Profile()
    #pr.enable()

    cursor = None
    canvases = next_canvas()
    while True:
        canvas = canvases.next()
        y, cursor = richtext.render(canvas, cursor=cursor)
        if cursor is None: break

    #pr.disable()
    #ps = pstats.Stats(pr)
    #ps.sort_stats("tottime")
    #ps.print_stats()

    home_path = os.getenv("HOME")
    fp = open(op.join(home_path, "Desktop", outfile_name), "w")
    outdoc.write_to(fp)
    fp.close()
