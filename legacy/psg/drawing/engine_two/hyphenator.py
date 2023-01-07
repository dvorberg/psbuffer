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
This module provides functionality to auto-hyphenate words using the PyHyphen
package.
"""

import re

try:
    import hyphen
except ImportError:
    hyphen = None

class hyphenator(object):
    """
    The hyphenator’s __call__() method will be handed a elements.word object
    and returns a list of syllables (not a new word object! The calling word
    will take care of managing its own syllables). If the hyphenator returns
    None, the word cannot be hyphenated.

    The default implementation uses PyHyphen.
    """
    def __init__(self, lang):
        if hyphen is None:
            raise ImportError("hyphen")
        self._hyphenator = hyphen.Hyphenator(lang)
        
    def syllables(self, word):
        """
        For `word` (a unicode string) return a list of
        syllables. (“Syllable” is a linguistic unit here and does NOT
        refer to the t4.psg.drawing.engine_two.elements.syllable class!)

        This is the only method you should need to overload.
        """
        return self._hyphenator.syllables(word)

    letters_re = re.compile(ur"(\w+)(.*)", re.UNICODE)
    def __call__(self, word):
        # We need to import elements here, because elements imports us
        # through style.        
        from t4.psg.drawing.engine_two import elements

        old_syllables = []
        text = []
        for syllable in word:
            for letter in syllable:
                text.append(letter)
                old_syllables.append(syllable)

        text = "".join(text)

        match = self.letters_re.match(text)
        if match is None:
            rest = ""
        else:
            text, rest = match.groups()        

        syllables = self.syllables(text)
        if not syllables:
            return None
            
        syllables[-1] += rest # Re-add the non-letter characters to the result.
        syllables = map(lambda s: list(s), syllables)

        lidx = 0
        for syllable in syllables:
            for i, letter in enumerate(syllable):
                syllable[i] = ( letter, old_syllables[lidx], )
                lidx += 1

        def split_syllable_by_style(syllable):
            ret = []
            current = None

            for letter, old_syllable in syllable:
                if old_syllable != current:
                    current = old_syllable
                    ret.append((current, [],))
                    
                ret[-1][1].append(letter)

            r = []
            for old_syllable, letters in ret[:-1]:
                r.append(elements.syllable( u"".join(letters),
                                            old_syllable._style,
                                            old_syllable._whitespace_style ))
                
            r.append(elements.syllable(u"".join(ret[-1][1]),
                                       ret[-1][0]._style,
                                       ret[-1][0]._whitespace_style,
                                       soft_hyphen=True))
                     
            return r


        syllables = map(split_syllable_by_style, syllables)
        
        ret = []
        for syllable in syllables:
            for kid in syllable:
                ret.append(kid)
                
        return ret
