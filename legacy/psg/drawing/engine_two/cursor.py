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

"""
The cursor class.
"""
import copy

class subcursor(object):
    """
    The subcursor class manages an index on a collection (a.k.a. list).
    It maintains relationships to a superior and an inferior cursor,
    allowing to navigate through a tree structure in-order, forward and
    backwards.
    """
    def __init__(self, superior):
        self.superior = superior
        self.superior.inferior = self
        
        self.inferior = None
        
        self.current_index = 0
        self._cache = None

    def reset(self):
        """
        Set the current index to 0. Also recursively reset inferior cursors.
        This makes us (and all our inferiors) point to the first child in the
        node they are responsible for.        
        """
        self._cache = None
        self.current_index = 0

        # Recursively reset my inferior(s).
        if self.inferior is not None:
            self.inferior.reset()
        
    def next(self):
        """
        Return the next object in our list or None, if we’re pointing at the
        last.
        """
        collection = self.superior.current()

        if self.current_index + 1 >= len(collection):
            return None
        else:
            return collection[self.current_index+1]

    def previous(self):
        """
        Return the previous object in our list or None, if we’re pointing at
        the first.
        """
        collection = self.superior.current()
        if self.current_index > 0:
            return collection[self.current_index-1]
        else:
            return None
    
    def current(self):
        """
        Return the object we’re pointing to.
        """
        if self._cache is None:
            collection = self.superior.current()
            self._cache = collection[self.current_index]
            
        return self._cache

    def advance(self):
        """
        Go forward by one object. If we’re at the end of a node, advance our
        parent cursor. This will make us point at the first element in the
        superior’s next(). 
        """
        if self.next() is None:
            if self.superior is not None:
                return self.superior.advance()
            else:
                return False
        else:
            self.current_index += 1
            self._cache = None  # Reset the cache.
            if self.inferior is not None:
                self.inferior.reset()
            return True

    def __call__(self):
        """
        Yield all objects in our list, starting with the current.
        """
        yield self.current()
        while self.advance():
            yield self.current()

class cursor(object):
    """
    A cursor object is a pointer to a specific location in a document tree.

    Objects of this class have four relevant properties: paragraphs, texts,
    words, syllables, each of which is a subcursor to the level in the
    model-tree its named after.
    """
    def __init__(self, document):
        self._document = document

        self._documents = subcursor(self) # There’s only one document
        self.paragraphs = subcursor(self._documents)
        self.texts = subcursor(self.paragraphs)
        self.words = subcursor(self.texts)
        self.syllables = subcursor(self.words)

    def clone(self):
        return copy.deepcopy(self)
        
    # We need to implement a minimum of the subcursor-class’ methods to
    # function as the root of the cursor tree.
    def current(self): return self._document
    def advance(self): return False


if __name__ == "__main__":
    words = [ [u"Ἐν"],
              [u"ἀρ", u"χῇ"],
              [u"ἦν"],
              [u"ὁ"],
              [u"λό", u"γος,"],
              [u"καὶ"],
              [u"ὁ"],
              [u"λό", u"γος"],
              [u"ἦν"],
              [u"πρὸς"],
              [u"τὸν"],
              [u"θε", u"όν,"],
              [u"καὶ"],
              [u"θε", u"ὸς"],
              [u"ἦν"],
              [u"ὁ"],
              [u"λό", u"γος."]]
    texts = [ words, ]
    paragraphs = [ texts, ]
    document = [ paragraphs, ]

    c = cursor(document)

    for a in c.syllables():
        print a


    
    
