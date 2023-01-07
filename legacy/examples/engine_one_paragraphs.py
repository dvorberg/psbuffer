#!/usr/bin/env python
# -*- coding: utf-8; -*-

import sys, os, os.path as op, re, time

from PIL import Image

from t4.debug import debug
#debug.verbose = True

from t4.psg.layout.engine_one import *
from t4.psg.exceptions import *
from t4.psg.util import *
from t4.psg.fonts.type1 import type1
from t4.psg.document.dsc import dsc_document
from t4.psg.drawing.box import canvas

import lorem_ipsum

def column_factory(document):
    while True:
        page = document.page("a4", None)

        h = mm(242.99)
        
        left = rectangular_column(
            canvas(page, mm(40), mm(25), mm(75), h, border=True))
        right = rectangular_column(
            canvas(page, mm(124.75), mm(25), mm(75), h, border=True))
        
        page.append(left.box())
        yield left
        
        page.append(right.box())
        yield right
        
def main():
    document = dsc_document()
    
    dir = op.dirname(__file__)
    if dir == "": dir = "."
    
    regular = type1(open(op.join(dir, "regular.pfb")),
                    open(op.join(dir, "regular.afm")))
    bold = type1(open(op.join(dir, "bold.pfb")),
                 open(op.join(dir, "bold.afm")))

    ue = style(font=bold, font_size=15, color="0 setgray",
               border_color=colors.rgb(1,0,0),
               name="ue")
    
    ga = style(font=regular, font_size=10, color="0 setgray",
               name="ga")
    
    section_fringes = style( margin_bottom=10, 
                             name="section_fringes")
    
    text = lorem_ipsum.ipsum
    paragraphs = split(text, "\n\n")
    paragraphs = map(strip, paragraphs)
    paragraphs = map(lambda s: splitfields(s), paragraphs)
    for counter, p in enumerate(paragraphs):
        p.insert(0, unicode(str(counter+1)))
                 
    #sections = map(lambda words: paragraph(words, ga), paragraphs)

    def make_paragraph(words):
        header = words[:6]
        return fringes(section_fringes,
                       headed_section( paragraph(ue, header),
                                       paragraph(ga, words),
                                       paragraph(ue, header + [u"(cont.)"]) ))
        
    sections = []

    image = Image.open("dog.jpg")
    sections.append(simple_raster_image(image))

    sections += map(make_paragraph, paragraphs)
    
    t = time.time()
    run_the_engine(column_factory(document), sections.__iter__())
    print time.time() - t
    
    document.write_to(open("out.ps", "w"))
    
main()
