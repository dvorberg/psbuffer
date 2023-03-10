#!/usr/bin/python
# -*- coding: utf-8; mode: python; ispell-local-dictionary: "english"; -*-

##  This file is part of psg, PostScript Generator.
##
##  Copyright 2014–23 by Diedrich Vorberg <diedrich@tux4web.de>
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
Cursor classes.
"""
import sys, dataclasses
import pdb

class CursorIsImmutable(Exception):
    pass

class RootCursor(object):
    def __init__(self, root_object):
        self.superior = None
        self.current = root_object
        self._current_index = 0
        self._cursors_by_name = {}

    def clone(self):
        return self.__class__(self.current)
    clone_immutably = clone

    def advance(self):
        return False

    def rewind(self):
        return False


class Cursor(object):
    def __init__(self, superior, attribute_name, current_index=0):
        self.superior = superior
        self.attribute_name = attribute_name
        self.superior.inferior = self
        self._cursors_by_name = self.superior._cursors_by_name
        self._cursors_by_name[self.attribute_name] = self
        self._was_at_end = False
        self.inferior = None

        self.current_index = current_index

    @classmethod
    def make_cursors_for(Cursor, root_object, attribute_names):
        leaf_cursor = RootCursor(root_object)
        for attribute_name in attribute_names:
            leaf_cursor = Cursor(leaf_cursor, attribute_name)

        return leaf_cursor

    def __iter__(self):
        while True:
            yield self.current
            if not self.advance():
                break

    def clone(self):
        return Cursor(self.superior.clone(),
                      self.attribute_name,
                      self._current_index)

    def clone_immutably(self):
        return ImmutableCursor(self.superior.clone_immutably(), self)

    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    def current_index(self, index):
        lst = getattr(self.superior.current, self.attribute_name)

        if index < 0:
            index = len(lst) + index

        self._current_index = index
        self.current = lst[index]

        self.first = (index == 0)
        self.last = (index == len(lst)-1)

    @property
    def max_index(self):
        return len(getattr(self.superior.current, self.attribute_name))-1

    def advance(self):
        """
        Go forward in the tree by one object. If we’re at the end
        of a node, advance our parent cursor. This will make us point
        at the first element in the superior’s next().

        Return True on success, False if we’re pointing at the last
        element in the tree.
        """
        if self.last:
            ret = self.superior.advance()
            self._was_at_end = True
            return ret
        else:
            self._was_at_end = False
            self.current_index += 1
            if self.inferior is not None:
                self.inferior.reset_to_first()
            return True

    def rewind(self):
        """
        Move the cursor back one element.
        """
        if self.current_index == 0:
            return self.superior.rewind()
        else:
            self.current_index -= 1
            if self.inferior is not None:
                self.inferior.reset_to_last()
            return True

    def reset_to_first(self):
        self.current_index = 0
        if self.inferior is not None:
            self.inferior.reset_to_first()

    def reset_to_last(self):
        self.current_index = -1
        if self.inferior is not None:
            self.inferior.reset_to_last()

    def __iter__(self):
        while True:
            yield self.current
            if not self.advance():
                break

    def next(self):
        if self.last:
            return None
        else:
            ret = self.current
            self.advance()
            return ret

    def __repr__(self):
        info = []
        cursor = self
        while cursor.superior is not None:
            if "paragraph" in cursor.attribute_name:
                current = f"<{cursor.current.__class__.__name__}>"
            else:
                current = repr(cursor.current)
            info.append(f"{cursor.attribute_name}[{cursor.current_index}]="
                        f"{current}" )
            cursor = cursor.superior
        return " ".join(info)

    def __bool__(self):
        return not self.last

    def hyphenate_current(self):
        """
        Walk up the object tree and find the first object that has a
        `hyphenate()` function. If found, call it, and reset the
        corresponding cursor.
        """
        here = self
        while hasattr(here, "current"):
            if hasattr(here.current, "hyphenate"):
                here.current.hyphenate()
                here.reset_to_first()
                return

            here = here.current

    def is_first_of(self, attribute_name):
        return self._cursors_by_name[attribute_name].first

    def is_last_of(self, attribute_name):
        return self._cursors_by_name[attribute_name].last

    def was_last_of(self, attribute_name):
        """
        Is the previous current at the very end of `attribute_name`?
        """
        # To be at the end of a level, all the inferior cursors
        # must be at their end.
        cursor = self._cursors_by_name[attribute_name]
        while cursor is not None:
            if not cursor._was_at_end:
                return False
            cursor = cursor.inferior

        return True

    def at_beginning_of(self, singular):
        """
        Are we currently at the start of an element?
        attribute_name = `singular` + "s"
        """
        # To be at the start all the cursor’s inferiors must be at 0.
        cursor = self._cursors_by_name[singular + "s"]
        while cursor.inferior is not None:
            cursor = cursor.inferior

            if cursor.current_index != 0:
                return False

        return True

    def at_end_of(self, singular):
        """
        Are we currently at the start of an element?
        attribute_name = `singular` + "s"
        """
        # To be at the very end, the cursor and
        # all the cursor’s inferiors must be at last.
        cursor = self._cursors_by_name[singular + "s"]
        while cursor is not None:
            if not cursor.last:
                return False
            cursor = cursor.inferior

        return True

    def current_of(self, attribute_name):
        return self._cursors_by_name[attribute_name].current


class ImmutableCursor(Cursor):
    """
    Copy over the relevant fields of a cursor. The clone() method
    will create a mutable clone out of this, if needed.
    """
    def __init__(self, superior, cursor: Cursor):
        self.superior = superior
        self.inferior = None
        self.superior.inferior = self
        self.attribute_name = cursor.attribute_name
        self._cursors_by_name = self.superior._cursors_by_name
        self._cursors_by_name[self.attribute_name] = self
        self._current_index = cursor.current_index
        self.last = cursor.last
        self.first = cursor.first

    @property
    def current(self):
        raise CursorIsImmutable()

    @Cursor.current_index.setter
    def current_index(self, index):
        raise CursorIsImmutable()

    def hyphenate_current(self):
        raise CursorIsImmutable()
