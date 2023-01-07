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

import re, types, unicodedata, copy, itertools
from string import *

from ll.xist import xsc

from t4.utils import here_and_next
from t4.web.typography import normalize_whitespace
from t4.psg.drawing.engine_two import elements, hyphenator
from t4.psg.util import colors

from t4.psg.drawing.engine_two.styles import style, text_style
from t4.cascading_style.constraints import one_of
from t4.psg.drawing.engine_two.styles.computer_modern import cmu_sans_serif
    
block_elements = { "blockquote", "body", "center", "col", "colgroup",
                   "dd", "div", "dl", "dt", "embed", "fieldset", "form", "h1",
                   "h2", "h3", "h4", "h5", "h6", "html", "hr", 
                   "li", "ol", "p", "pre", "script", "style",
                   "table", "tbody", "td", "tfoot", "th",
                   "thead", "tr", "tt", "ul", }
inline_elements = { "a", "abbr", "acronym", "address", "b", "bdo", "big",
                    "caption", "cite", "code", "del", "dfn", "dir", "em",
                    "font", "i", "ins", "kbd", "label", "legend", "menu",
                    "nobr", "q", "s", "samp", "small", "span", "strike",
                    "strong", "sub", "sup", "u", "var", }

# These elements will be ignored when encountered in the DOM tree.
ignored_elements = { "applet", "area", "base", "basefont", "button", "frame",
                     "frameset", "iframe", "head", "img", "input", "isindex",
                     "link", "map", "meta", "noframes", "noscript", "object",
                     "optgroup", "option", "param", "select", "textarea",
                     "title", }

class htmsty(style):
    """
    The style object for HTML elements contains an additional field
    called display that acts much like the CSS display: property and
    defines how an element is drawn.
    """    
    __constraints__ = { "display": one_of( {"block", "inline", "none"}), }

inline_style = htmsty({"display": "inline"}, name="inline")
block_style = htmsty({"display": "block"}, name="block")

specifics = { "html": cmu_sans_serif,
              "a": text_style({"color": colors.blue}),
              "b": text_style({"font-weight": "bold"}),
              "big": text_style({"font-size": 20, "line-height": 22}),
              "em": text_style({"text-style": "italic"}),
              "i": text_style({"text-style": "italic"}),
              "small": text_style({"font-size": 8}),
              "strong": text_style({"font-weight": "bold"}), }

def assemble(tag, model_style):
    style = model_style + specifics.get(tag, {})
    style.set_name(tag)
    return tag, style,

default_styles = dict(itertools.chain(map(lambda tg: assemble(tg, block_style),
                                          block_elements),
                                      map(lambda tg: assemble(tg, inline_style),
                                          inline_elements)))

def convert(element, styles={}):
    """
    Convert the XIST DOM tree referenced by `frag` to a
    engine_two.model-tree that can be rendered to PostScript using the
    engine. The style provided for `element`s tag in `styles` must be
    complete. It will be passed to the returned elements.richtext object.
    """
    # Fill in the gaps in the styles dict.
    styles = copy.copy(styles)
    for tag, style in default_styles.iteritems():
        if styles.has_key(tag):
            styles[tag] = default_styles[tag] + styles[tag]
            styles[tag].set_name("usr" + tag.upper())
        else:
            styles[tag] = default_styles[tag]

    def style(element):
        """
        Return the style from the `styles` parameter keyd to `element` by
        its class name, i.e. its HTML tag.
        """
        return styles[element.__class__.__name__]
        
    def boxes(element):
        current_text_elements = []
        
        for child in element:            
            if isinstance(child, xsc.Text) or style(child).display == "inline":
                current_text_elements.append(child)
            else:
                # It’s a block element
                if len(current_text_elements) > 0:
                    yield paragraph(current_text_elements)
                    current_text_elements = []

                yield elements.box(boxes(child), style=style(child))
                
        if len(current_text_elements) > 0:
            yield paragraph(current_text_elements)

    def paragraph(text_elements):
        return elements.paragraph(words(text_elements))
            
    def words(text_elements):
        word = elements.word()
        for element in text_elements:
            if isinstance(element, xsc.Text):
                mystyle = None
                element = [ element, ]
            else:
                mystyle = style(element)

            for child in element:
                for (syllable, starts_word, ends_word,)  in syllables(
                        child, mystyle):
                    if starts_word and len(word) > 0:
                        word[-1]._whitespace_style = syllable._style
                        yield word
                        word = elements.word()
                        
                    word.append(syllable)
                    
                    if ends_word:
                        yield word
                        word = elements.word()
                        
        if len(word) > 0:
            yield word

    word_re = re.compile(r"(\S+)(\s*)")
    starts_word_re = re.compile(r"^\s+")
    def syllables(element, span_style=None):
        if isinstance(element, xsc.Text):
            u = element.__unicode__()

            match = starts_word_re.search(u)
            starts_word = (match is not None)
            
            for letters, whitespace in word_re.findall(u):
                ends_word = ( whitespace != u"" )
                if ends_word:
                    whitespace_style = span_style
                else:
                    whitespace_style = None
                    
                yield ( elements.syllable(letters, span_style,
                                          whitespace_style), 
                        starts_word, ends_word, )
                starts_word = False
        else:
            mystyle = style(element)
            assert mystyle.display == "inline", ValueError(
                "Inline elements may not contain block elements.")
            
            for child in element:
                for syllable in syllables(child, mystyle):
                    yield syllable

    return elements.richtext(boxes(element), style=style(element))


    
if __name__ == "__main__":
    import sys, os, os.path as op
    
    from t4.psg.drawing.engine_two.styles import lists
    from t4.psg.drawing.engine_two.styles.computer_modern \
      import cmu_sans_serif as cmuss, style
    from t4.psg.util.colors import red
    from t4.psg.drawing.engine_two.processors import render_to_filename

    from ll.xist.ns import html, chars

    demo = html.html(html.p(u"Hallo ", html.strong("schöne "), u"Welt!"),
                     html.p(u"DiesesWort",
                            html.strong(u"Keine"),
                            u"Leerzeichen."),
                     html.p(u"Dieses",
                            html.big(" Leerzeichen "),
                            u"ist groß."),
                     html.p(u"Dieses ",
                            html.big("Leerzeichen"),
                            u" ist klein."))

    richtext = convert(demo, {"p": {"margin": (12, 0, 0, 0)}})
    
    print
    richtext.__print__()

    render_to_filename(richtext, "xist.ps")

        
    
