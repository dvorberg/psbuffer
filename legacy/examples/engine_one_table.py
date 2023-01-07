#!/usr/bin/env python
# -*- coding: utf-8; -*-

import sys, os, os.path as op, re, time

from t4.debug import debug
#debug.verbose = True

from t4.psg.layout import engine_one as engine

from t4.psg.exceptions import *
from t4.psg.util import *
from t4.psg.fonts.type1 import type1
from t4.psg.document.dsc import dsc_document
from t4.psg.drawing import box

def column_factory(document):
    while True:
        page = document.page("a4", None)
        canvas = box.canvas(page, mm(20), mm(20),
                            page.w() - mm(40), page.h() - mm(40))
        page.append(canvas)
        yield engine.rectangular_column(canvas)
        
def bg(idx):
    if idx == 0:   rgb = (1, 0, 0)
    elif idx == 1: rgb = (0, 1, 0)
    elif idx == 2: rgb = (0, 0, 1)
    elif idx == 3: rgb = (1, 1, 0)
    elif idx == 4: rgb = (0, 1, 1)
    elif idx == 7: rgb = (1, 1, 0)
    
    elif idx == 5: rgb = (0, 0.5, 0)
    elif idx == 10: rgb = (0, 0.5, 0)
    elif idx == 9:  rgb = (0, 0, 0.5)
    elif idx == 11:  rgb = (0.5, 0.5, 0)
    elif idx == 6:  rgb = (0, 0.5, 0.5)
    elif idx == 8:  rgb = (0.5, 0.5, 0)
    
    return engine.style(background_color=colors.rgb(*rgb))

def main():
    document = dsc_document()
    
    dir = op.dirname(__file__)
    if dir == "": dir = "."
    
    regular = type1(open(op.join(dir, "regular.pfb")),
                    open(op.join(dir, "regular.afm")))
    bold = type1(open(op.join(dir, "bold.pfb")),
                 open(op.join(dir, "bold.afm")))

    ue = engine.style(font=bold, font_size=15, color="0 setgray",
                      border_color=colors.rgb(1,0,0),
                      name="ue")
    
    ga = engine.style(font=regular, font_size=10, color="0 setgray",
                      name="ga")

    head_style = engine.style(background_color = colors.grey(0.5),
                              margin_bottom=10)
                              
    
    table_style = engine.style(margin_bottom=10,
                               border = (0.5, 0.5, 0.5, 0.5,),
                               border_color = colors.grey(0),
                               #background_color=colors.gray(0.5)
                               )
    row_style = engine.style()
    cell_style = engine.style(border = (0.5, 0.5, 0.5, 0.5,),
                              border_color = colors.grey(0),
                              padding = (10,10,10,10),
                              #background_color=grey(0.5)
                              )

    
    table = engine.table(
        table_style,
        ( mm(20), mm(20), ),
        engine.row(head_style,
                   engine.cell(cell_style,
                               engine.simple_paragraph(ga, [u"Links"])),
                   engine.cell(cell_style,
                               engine.simple_paragraph(ga, [u"Rechts"]))))

    for a in range(50):
        table.append(engine.row(row_style,
                                engine.cell(cell_style + bg(0),
                                            engine.simple_paragraph(ga,
                                                                    [str(a)])),
                                engine.cell(cell_style + bg(1),
                                            engine.simple_paragraph(ga,
                                                                    str(a*2)))))

    
    table2 = engine.table(
        table_style,
        ( mm(20), ),
        None,
        engine.row(row_style,
                   engine.cell(cell_style + bg(4),
                               engine.simple_paragraph(ga, [u"Stephi",]))))

    p = engine.paragraph(cell_style + ga + bg(3) + engine.style(margin_top=30),
                         [u"Hello", u"World!"])
    
    sections = [table, table2, p] 

    t = time.time()
    engine.run_the_engine(column_factory(document), sections.__iter__())
    print time.time() - t
    
    document.write_to(open("out.ps", "w"))
    
main()
