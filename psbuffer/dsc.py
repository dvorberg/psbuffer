#!/usr/bin/python
# -*- coding: utf-8; mode: python; ispell-local-dictionary: "english"; -*-

##  This file is part of psg, PostScript Generator.
##
##  Copyright 2006-23 by Diedrich Vorberg <diedrich@tux4web.de>
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
This module provides classes that model the PostScript Language
Document Structuring Conventions as described in Adobe's Specifications
Version 3.0 available at
U{http://partners.adobe.com/public/developer/ps/index_specs.html}.
"""

import collections.abc

from .base import PSBuffer, encode
from .utils import ps_escape

def ps_literal(value) -> bytes:
    """
    Convert Python primitive into a DSC literal. This will use
    Python's str() function on the value, because it produces ideal
    results for integer and float values. Strings will be quoted
    according to the DSC's rules as layed out in the specifications on
    page 36 (section 4.6, on <text>).
    """
    if type(value) in ( str, bytes ):
        return ps_escape(value)
    else:
        return encode(str(value))


class Comment(object):
    """
    A DSC comment, starting with %% and contains `args`.
    """
    def __init__(self, keyword:str, value):
        self.keyword = self.keyword
        self.set(value)

    def set(self, value):
        self._value = value

        if type(self._value) in (str, bytes, int, float):
            self._payload = ps_literal(value)
        elif isinstance(value, collections.abc.Sequence):
            self._payload = [ ps_literal(a) for a in value ].join(b" ")
        else:
            raise TypeError("Can’t handle " + repr(value))

    @property
    def value(self):
        return self._value

    def __bytes__(self):
        if not self.args:
            return b"%%" + self.keyword + b"\n"
        elif self.keyword == b"+":
            return b"%%+ " + self._payload + b"\n"
        else:
            return b"%%" + self.keyword + b": " + self._payload + b"\n"

class CommentProperty(property):
    def __init__(self, comment_keyword):
        self.comment_keyword = comment_keyword

    def __get__(self, section, owner=None):
        if section.has_comment(self.comment_keyword):
            return getattr(section, self.comment_keyword)
        else:
            return None

    def __set__(self, section, value):
        section.set_comment_value(self.comment_keyword, value)


class Resource(object):
    """
    Model a DSC resource. A resource has

    - a type (one of font, file, procset, pattern, form, encoding)
    - a name
    - maybe a resource_section
    - maybe a list of setup lines
    """
    def __init__(self, type, name, section=None, setup_lines=None):
        self.type = type
        self.name = name
        self.section = section
        self.setup_lines = setup_lines

class CommentCache(dict):
    def __init__(self, *initial_comments):
        dict.__init__(self)

        for comment in initial_comments:
            self.add(comment)

    def add(self, comment:Comment):
        self[comment.keyword] = comment

    def __contains__(self, key):
        return dict.__contains__(self, key)

    def __setitem__(self, key, comment:Comment):
        self.add(comment)

    def __getitem__(self, key):
        return dict.__getitem__(self, key)

    def get(self, key, default=sys):
        ret = dict.get(self, key, default)
        if ret is sys:
            raise KeyError(key)
        else:
            return ret


class SectionCache(list):
    def add(self, section):
        self.append(section)

    def __contains__(self, name):
        return bool(self.by_name(name))

    def by_name(self, name):
        return [ s for s in self if s.name == name ]


class Section(PSBuffer):
    """
    Abstract class.

    Model a section of a postscript document. A section is a PSBuffer that
    has three types of entries:

      - strings - containing PostScript
      - comments - instances of the comment class above
      - other sections

    A section's name will be used for the Begin(End)Section keywords,
    unless these are overwriten by the constructor's begin/end
    arguments.

    The section object will have one attribute for each DSC comment it
    contains. If two DSC comments with the same name are added to the
    section, an exception will be raised.

    Sections may be nested. Sections of the same name are allowed, but
    sections with the same name and the same argument list are
    not. Just as with comments, the section will have attributes
    refering to its subsection by their name. The name will always
    point to the first section added by that name.

    The structur of a dsc_document is as follows::

       dsc_document
          Header -- section

          Defaults -- section

          Proplog -- section
             Resource0
             Resource1
             ...

          Setup -- section

          Pages -- (pseudo) section

             Page -- section
               PageSetup -- section
               .. Lots of PS ..
               PageTrailer -- section

             Page -- section
               PageSetup -- section
               .. Lots of PS ..
               PageTrailer -- section

             ...

          Trailer


    This diverges slightly from the Document Structuring Convention
    Specification's understanding as expressed in Figure 1 on page 19,
    in which the Header is understood as part of the Prolog. (It does
    make sense to view it as part of the Prolog since it's not part of
    the rest of the file.

    @cvar begin: Comment that starts this section in its parent section
    @cvar end: Comment that ends this section and makes the parser hand
       back controll to its caller.
    @cvar subsections: List of strings naming section_?? classes of those
       subsections that may occur in this section.
    @cvar mandatory: Boolean indicating whether this section MUST be present
       in its parent section (meaningfull only for the first or the last
       section in the subsection list). If a section is mandatory its begin
       or(!) end keyword may be None. The pages_section is an exception to
       this rule.
    """
    begin_keyword = None
    end_keyword = None
    possible_subsections = ()
    mandatory = False

    def __init__(self, *begin_args):
        """
        The arguments passed will be put into the beginning comment.
        Remains unused if `begin_keyword` is None.
        """
        PSBuffer.__init__(self)

        self._comment_cache = CommentCache(self.begin)
        self._subsection_cache = SectionCache()

        if self.begin_keyword:
            self.begin = Comment(self.begin_keyword, *begin_args)
            self.append(self.begin)
        else:
            self.begin = None

        # Will be written in write_to()
        if self.end_keyword:
            self.end = Comment(self.end_keyword)
        else:
            self.end = None

    def write(self, *things):
        for thing in things:
            if isinstance(thing, Comment):
                self._comment_cache.add(thing)
            elif isinstance(thing, Section):
                self._subsection_cache.add(thing)

        PSBuffer.write(self, *things)

    append = write

    # Comment management
    def has_comment(self, keyword):
        return keyword in self._comment_cache

    def set_comment_value(self, keyword, value):
        if self.has_comment(keyword):
            self.comment(keyword).set(value)
        else:
            comment = Comment(keyword, value)
            self.append(comment)

    def comment(self, comment_keyword):
        return self._comment_cache.get(comment_keyword)

    def comments(self):
        """
        Return an iterator over the comments in this section.
        """
        return self._comment_cache.values()

    # Subsection management
    def has_subsection(self, name):
        """
        Determine whether this section contains a subsection by that name.
        """
        return name in self._subsection_cache

    def subsections(self, name=None):
        """
        Return an iterator over of this sections subsections.

        @param name: Return only those subsections whoes name is 'name'.
        """
        if name is None:
            return self._section_cache.copy()
        else:
            return self._section_cache.by_name(name)

    def write_to(self, fp):
        PSBuffer.write_to(self, fp)

        if self.end is not None:
            fp.write(bytes(self.end))

    def __repr__(self):
        return "<%s %s %s (%i subsections)>" % (self.__class__.__name__,
                                                self.name,
                                                repr(self.begin.value),
                                                len(list(self.subsections())),)


    @property
    def name(self):
        return self.__class__.__name__[:-len("Section")]






class atend(object):
    pass
AtEnd = atend()
