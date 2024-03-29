#!/usr/bin/python
# -*- coding: utf-8; mode: python; ispell-local-dictionary: "english"; -*-

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
This module provides classes that model the PostScript Language
Document Structuring Conventions as described in Adobe's Specifications
Version 3.0 available at
U{http://partners.adobe.com/public/developer/ps/index_specs.html}.
"""


# Python
import sys, re, warnings
from string import *
from types import *

from cStringIO import StringIO as cStringIO # need both of them for isinstance()
from StringIO import StringIO

from t4.debug import debug

# psg
from t4.psg.util import *
from t4.psg.document.document import *
from t4.psg.fonts.type1 import type1


# Utility functions

def literal(value):
    """
    Convert Python primitive into a dsc literal. This will use
    Python's str() function on the value, because it produces ideal
    results for integer and float values. Strings will be quoted
    according to the DSC's rules as layed out in the specifications on
    page 36 (section 4.6, on <text>).
    """
    if type(value) == StringType:
        if " " in value:
            return "(%s)" % value
        else:
            return value
    else:
        return str(value)

dsc_literal_re = re.compile(r"(-?\d*\.\d+(?:e\d+)?)|"  # float    -1.2e3, .5
                            r"(-?\d+)|"                # int      1234
                            r"\((.*)\)|"               # () ps string
                            r"(\S+)"                   # regular string
                            )

escape_re = re.compile(r"\\([ntr]{1}|[01234567]{1,3})")

class atend: pass
AtEnd = atend()

def parse_literals(line, schema="l"):
    r"""
    The parses DSC elementaty type literals into Python primitives. It
    depends on a line schema, which is a string any combination of l,
    s, i, f, which stand for line, string, integer and float
    respectively.

    A BoundingBox may be parsed by::

      'iiii' -> '0 0 100 100' => ( 0, 0, 100, 100, )

    A BeginResource info::

      'ssff' -> 'procset Adobe_AGM_Utils 1.0 0' => ( 'procset',
                                                     'Adobe_AGM_Utils',
                                                     1.0, 0.0, )
    A Document Title::

      'l' -> 'Diedrich''s Document 123' -> ( 'Diedrich''s Document 123', )

    If you specify l you can't specify anything else.

    Strings in Parentheses will be searched for escape sequences \\,
    \123 (oct byte representation), \n, \t, and \r. These will be
    repleced by appropriate bytes.

    If the content of the DSC Comment is (atend), this function will
    return the AtEnd object defined above.

    @param line: String containing the elementary type literals (a DSC
      comment line after the :)
    @param schema: Line schema.
    @raises DSCSyntaxError:
    @returns: Either a tuple of Python primitives or the AtEnd object
    """
    if line is None:
        return None
    if strip(line) == "(atend)":
        return AtEnd
    elif schema == "l":
        return line
    else:
        result = dsc_literal_re.findall(line)

        #if len(result) != len(schema):
        #    msg = "Argument line %s does not match schema %s." % ( repr(line),
        #                                                            schema, )
        #    raise DSCSyntaxError(msg)


        if len(result) > len(schema):
            result = result[:len(schema)]
        elif len(schema) > len(result):
            schama = schema[:len(result)]


        ret = []
        for char, tpl in zip( schema, result ):
            if char == "f":
                f = tpl[0] or tpl[1] # a float without a . in it will end up
                                     # in the integer slot

                try:
                    f = float(f)
                    ret.append(f)
                except ValueError:
                    msg = "Can't parse %s to float " +\
                          "(argument schema mismatch?)"
                    msg = msg % repr(f)
                    raise DSCSyntaxError(msg)

            elif char == "i":
                i = tpl[1]
                try:
                    i = int(i)
                except ValueError:
                    msg = "Can't parse %s to int "+\
                          "(argument schema mismatch?)"
                    msg = msg % repr(i)
                    raise DSCSyntaxError(msg)

                ret.append(i)

            elif char == "s":
                if tpl[3]:
                    ret.append(tpl[3])
                elif tpl[2]:
                    # perform escaping
                    patrs = escape_re.split(tpl[2])
                    parts.reverse()

                    s = []
                    while parts:
                        s.append(parts.pop())

                        if parts:
                            seq = parts.pop()

                            if seq == "n":
                                s.append("\n")
                            elif seq == "t":
                                s.append("\t")
                            elif seq == "r":
                                s.append("\r")
                            else:
                                s.append(chr(int(seq, 8)))

                    ret = join(s, "")

                else:
                    ret.append("")
            else:
                raise ValueError("Illegal schema identifyer: %s" % char)

        return tuple(ret)



class parsed_property(property):
    """
    Properties of a DSC document's subsection that directly correspond
    to DSC comments. This class parses the DSC comment on __get__()
    and creates a correct DSC comment on __set__().
    """
    def __init__(self, comment_keyword, argument_schema="l",
                 atend=False):
        """
        @param comment_keyword: Keyword of the respective DSC comment
        @param argument_schema: Schema as for the parse_literals() function
           above
        @param path: Attribute path to the property if it is not present
           in the current section. If a path element contains a space and a
           number n, the nth subsection of that name will be queried
           (0 based!). Examle:

             - ( 'Prolog', ) -- The current section's Prolog attribute
             - ( 'Page 0', 'PageSetup', ) -- Setup section of the first page

           note that not the section is returned, but the attribute named
           comment_keyword of that section.
        @param atend: If atend is specified, the current document's Trailer
           section is checked for comment_keyword if the original target
           section contained the (atend) token.
        """
        self.comment_keyword = comment_keyword
        self.argument_schema = argument_schema
        self.atend = atend

    def __get__(self, section, owner=None):
        """
        Return the parsed_property for that section. None if it cannot
        be found.
        """
        comment = self.comment(section)

        if comment is None:
            return None
        else:
            return self.process_comment(comment)

    def __set__(self, section, value):
        """
        Make sure the input value is a value like the one __get__
        would return. It must match you argument schema. (In other words,
        value should be a tuple. If the schema is 'l' or a single value,
        it may be a single primitive).
        """
        if self.argument_schema != "l":
            if len(self.argument_schema) == 1 and type(value) != TupleType:
                value = ( value, )

            ret = []
            for char, val in zip(self.argument_schema, value):
                format = "%%%s" % char
                ret.append(format % val)

            value = join(ret, " ")

        cmt = section.comment(self.comment_keyword)
        if cmt is None:
            section.append(comment(self.comment_keyword, value))
        else:
            cmt.set(value)

    def process_comment(self, comment):
        tpl = parse_literals(comment.info, self.argument_schema)
        if tpl is not None and tpl != AtEnd and len(self.argument_schema) == 1:
            return tpl[0]
        else:
            return tpl


    def comment(self, section):
        return getattr(section, self.comment_keyword, None)

class comment:
    """
    A DSC comment, starting with %% and containing zero or more
    arguments.
    """
    def __init__(self, name, _info=None, *args):
        self.name = name

        if _info is not None:
            self.info = strip(_info)
        else:
            self.info = None

        if len(args) == 0:
            self.args = None
        else:
            args = map(literal, self.args)
            self.info = join(args, " ")


    def __str__(self):
        """
        Return a DSC comment as a string, as

        C{%%Name}

        if len(args) is 0 or

        C{%%Name: <arg0> <arg1> ...}

        otherwise.
        """
        if self.info is None:
            return "%%" + self.name + "\n"
        elif self.name == "+":
            return "%%+ " + self.info + "\n"
        else:
            return "%%" + self.name + ": " + self.info + "\n"

    def set(self, value):
        if type(value) == StringType:
            self.args = ( value, )
            self.info = value

        elif type(value) == UnicodeType:
            raise TypeError("No Unicode allowed in dsc_documents")

        else: #elif type(value) == ListType:
            self.args = tuple(value)
            value = map(lambda s: ps_escape(s, False), value)
            self.info = join(value, " ")



class string_list_property(parsed_property):
    def __init__(self, keyword, atend=False):
        parsed_property.__init__(self, keyword, atend=atend)

    element_re = re.compile(r"\(.*?\)|\S+")
    def process_comment(self, comment):
        ret = self.element_re.findall(cmt)
        for counter, s in enumerate(ret):
            if len(s) >= 2 and s[0] == "(" and s[-1] == ")":
                ret[counter] = s[1:-1]

        return map(remove_parenthesis, ret)

    def __get__(self, section, owner=None):
        comment = section.comment(self.comment_keyword)
        if comment is None:
            return None
        else:
            if isinstance(string_list_comment):
                return comment.lst
            else:
                # Use parsed_property's mechanism to return a result
                ret = parsed_property.__get__(self, section, owner)

                if ret is None:
                    return []
                else:
                    return ret

    def __set__(self, section, value):
        """
        @param value: A list of strings
        """
        comment = section.comment(self.comment_keyword)
        if comment is None:
            section.append(string_list_comment(self.comment_keyword, value))
        else:
            if isinstance(comment, string_list_comment):
                comment.set(value)
            else:
                comment.set(join(map(lambda s: ps_escape(s, False),
                                     value), " "))

class string_list_comment(comment):
    def __init__(self, name, lst):
        comment.__init__(self, name)
        self.lst = lst

    def __str__(self):
        return "%%" + self.name + ": " + join(map(lambda a:ps_escape(s, False),
                                                  self.lst), " ")

    def set(self, value):
        self.lst = value

class resources_property(parsed_property):
    """
    A resource property will contain a resource_set instance.
    """
    def __init__(self, keyword, atend=False):
        parsed_property.__init__(self, keyword, atend=atend)

    def process_comment(self, comment):
        return dsc_resource_set.from_string(comment.info)

    def __set__(self, section, value):
        for a in value.as_comments(self.comment_keyword):
            if not hasattr(section, a.name):
                section.append(a)



class multiple_subsections(property):
    """
    Return all subsections from a section with a particular name.
    """
    def __init__(self, section_name):
        self.section_name = section_name

    def __get__(self, section, owner=None):
        return list(section.subsections(self.section_name))


class dsc_resource(resource):
    """
    Model a DSC resource. A resource has

      - a type (one of font, file, procset, pattern, form, encoding)
      - a name
      - maybe a version
      - maybe a resource_section
      - maybe a list of setup lines

    In case the resource has a version, the version will be part of
    the name string as well as being represented as a tuple of float
    in the version attribute. (This is only true for procsets, by the
    way).

    To construct a new resource object from scratch you'll need the
    PostScript source that goes into its resource section and
    (optinally) the lines that go into the document's or page's Setup
    section to initialize the resource.

    When read from an existing PostScript file the Setup lines may be
    missing although they are mandatory for the resource to actually
    work. Unfortunately it is impossible to identify which lines belong
    to which resource by reading a DSC compilent PostScript file. It
    is also impossible to resolve interdependencies between resources
    (which ones have to be there and have to be initialized before the
    others). As a result the Prolog and Setup section of a Postscript
    file can only be 'transplanted' as a whole, carefully maintaining
    the order of resources and lines. The interplay between Resource
    and Setup sections can never be reconstructed comletly, can never
    be 100% reliable.
    """
    def __init__(self, type, name, section=None, setup_lines=None):
        resource.__init__(self, type, name, ())
        self.procset_name = None
        self.section = section
        self.setup_lines = setup_lines

        if type == "procset":
            parts = splitfields(name)
            self.procset_name = parts[0]

            if len(parts) != 3:
                self.version = 0.0, 0.0
            else:
                self.version = ( float(parts[1]), float(parts[2]), )

    def from_string(cls, s, section=None):
        parts = splitfields(s)

        if len(parts) == 1:
            rest = ""
        else:
            rest = join(parts[1:], " ")

        type = strip(parts[0])

        return cls(type, rest, section)

    from_string = classmethod(from_string)

    def as_string(self):
        return "%s %s" % ( self.type, self.name, )

    def from_section(cls, resource_section):
        return cls.from_string(resource_section.info, resource_section)

    from_section = classmethod(from_section)

    def __eq__(self, other):
        if self.type == other.type and self.name == other.name:
            return True
        else:
            return False

class dsc_resource_set(resource_set):
    """
    A set of resource identifyers. The add() function will take care
    that there is only one mentioning of a resource in the
    set. Procsets are treated specially, as procsets with a lower
    version number will be replaced by procsets with the same name and
    a higher version number.

    The class' constructor accepts a string as argument that's the
    argument of a DSC comment containing several resource identifyers.
    """
    part_re = re.compile(r"(\(.*?\)|\S+)")

    resource_types = ( "font", "file", "procset", "pattern",
                       "form", "encoding", )

    def from_string(cls, s=""):
        s = strip(s)
        parts = cls.part_re.findall(s)

        self = cls()

        parts.reverse()
        current_type = None
        while parts:
            part = strip(parts.pop())

            if part == "procset":
                # A procset name may be 'name maj min' or 'name (maj min)'
                name = parts.pop()
                next = parts.pop()

                if next[0] == "(" and next[-1] == ")":
                    major, minor = splitfields(next[1:-1])
                else:
                    major = next
                    minor = parts.pop()

                self.add( dsc_resource("procset",
                                       "%s %s %s" % ( name, major, minor, )) )
            else:
                if part in cls.resource_types:
                    keyword = part
                else:
                    self.add( dsc_resource(keyword, part) )




        return self

    from_string = classmethod(from_string)

    def as_comments(self, comment_keyword):
        """
        Return a generator of comment instances representing the
        resource set.
        """
        for counter, a in enumerate(self):
            if counter == 0:
                yield comment(comment_keyword, a.as_string())
            else:
                yield comment("+", a.as_string())





# Section

def _subsection_class(name):
    """
    Helper function that returns a class for a subsection name
    """
    return globals()["%s_section" % lower(name)]

class section(file_like_buffer):
    """
    Model a section of a postscript document. A section is a composition
    buffer that has three types of entries:

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

    @ivar subfile: A subfile is either None (the section is
       constructed from scratch) or a file object (the section has been
       parsed from an existing PostScript document). If it is a file
       pointer, the file must contain the Begin(End)Lines, whereas the
       section itself (as a file like buffer) does not contain these
       but adds then in write_to()

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
    comment_re = re.compile(r"^%%[A-Za-z0-1\+]+.*?$")

    begin = None
    end = None
    possible_subsections = ()
    mandatory = False

    def __init__(self, info=None, empty=False, subfile=None):
        """
        """
        file_like_buffer.__init__(self)

        self.info = info
        if subfile is not None:
            self.subfile = subfile

    def has_comment(self, comment_keyword):
        ret = self.comment(comment_keyword)
        if ret is None:
            return False
        else:
            return True

    def comment(self, comment_keyword):
        for a in self.comments():
            if a.name == comment_keyword:
                return a
        else:
            return None

    def comments(self):
        """
        Return an iterator over the comments in this section.
        """
        for a in self.__dict__.values():
            if isinstance(a, comment):
                yield a


    def has_subsection(self, name, info=None):
        """
        Determine whether this section contains a subsection by that name
        and argument list.
        """
        name = lower(name)
        if info is not None:
            for subsection in self.subsections():
                if subsection.name() == name and subsection.info == info:
                    return True
        else:
            for subsection in self.subsections():
                if subsection.name() == name:
                    return True

        return False

    def subsections(self, name=None):
        """
        Return an iterator over of this sections subsections.

        @param name: Return only those subsections whoes name is 'name'.
        """
        if name is None:
            for a in self:
                if isinstance(a, section):
                    yield a
        else:
            name = lower(name)
            for a in self:
                if isinstance(a, section) and a.name() == name:
                    yield a


    def as_string(self):
        if hasattr(self, "subfile"):
            self.subfile.seek(0)
            return self.subfile.read()
        else:
            return file_like_buffer.as_string(self)

    __str__ = as_string

    def write_to(self, fp):
        if hasattr(self, "subfile"):
            self.subfile.seek(0)
            copy_linewise(self.subfile, fp)
        else:
            if self.begin is not None:
                if self.info:
                    print >> fp, "%%" + self.begin + ":", self.info
                else:
                    print >> fp, "%%" + self.begin

            file_like_buffer.write_to(self, fp)

            if self.end is not None:
                print >> fp, "%%" + self.end

    def append(self, what):
        """
        If what is a comment, add an attribute to this object by
        the comment's name referring to the comment itself. If a comment
        by that name already exists, raise AttributeError.

        If the last element in this section is its Trailer section,
        this function will make sure that the trailer stays at the
        very end of the section.
        """
        if what is None:
            return

        if isinstance(what, comment) and what.name != "+":
            if hasattr(self, what.name):
                raise AttributeError(
                    "A DSC Comment %s already exists in this section!" % \
                    repr(what.name))
            else:
               setattr(self, what.name, what)

        if isinstance(what, section):
            if self.has_subsection(what.name(), what.info):
                msg = "A subsection %s %s already exists in this section."
                msg = msg % ( repr(what.name()), repr(what.info), )
                raise AttributeError(msg)

            if not hasattr(self, what.name()):
                setattr(self, what.name(), what)

        file_like_buffer.append(self, what)

    def __repr__(self):
        return "<%s %s %s (%i subsections)>" % (self.__class__.__name__,
                                                self.name(),
                                                repr(self.info),
                                                len(list(self.subsections())),)


    def parse(cls, parent, lines, level=1):
        print >> debug, ">>" * level, cls.name()

        # On entry to the parse() function the file pointer must be set
        # to the begining of the first line of this section's content.
        start_seek_pointer = lines.fp.tell()

        info = None
        if cls.begin is not None:
            # Skip our start line.
            line = lines.next()

            # Disassemble the keyword
            parts = split(line, ":", 1)
            keyword = parts[0]

            if len(parts) > 1:
                info = parts[1]
            else:
                info = ""

        self = cls(info=info, empty=True)

        # This section has a header.
        if len(cls.possible_subsections) > 0 and \
               _subsection_class(cls.possible_subsections[0]).mandatory:
            c = _subsection_class(cls.possible_subsections[0])
            c = c.parse(self, lines, level+1)
            self.append(c)

        try:
            last_comment = None
            while True:
                # Seek forward to the next DSC comment
                line = lines.next()
                while not line.startswith("%%"):
                    line = lines.next()

                line = strip(line)

                #print >> debug, cls.name(), repr(line)[:60]

                line = line[2:]

                # Here's another exception: In a Resource section the
                # lines after the EndResource up the next
                # BeginResource or the EndProlog are considered part
                # of the Resource.  That's because when
                # 'transplanting' a resource we're going to need those
                # initialization lines.
                if line == cls.end:
                    if cls.__name__ == "resource_section":
                        while not line.startswith("%%"):
                            line = lines.next()
                        lines.rewind()

                    raise StopIteration

                if parent is not None and line == parent.end:
                    lines.rewind()
                    raise StopIteration

                # Disassemble the keyword
                parts = split(line, ":", 1)
                keyword = parts[0]

                if len(parts) > 1:
                    info = parts[1]
                else:
                    info = ""

                print >> debug, "++" * level, repr(keyword), repr(info)

                # Collect possible peer and subsection keywords
                subsection_keywords = {}
                for a in cls.possible_subsections:
                    c = _subsection_class(a)
                    if c.begin is not None:
                        subsection_keywords[c.begin] = c

                peer_keywords = []
                if parent is not None:
                    for a in parent.possible_subsections:
                        c = _subsection_class(a)
                        if c.begin is not None:
                            peer_keywords.append(c)

                if keyword == page_section.begin:
                    # If the keyword is "Page" pass controll to a
                    # pages_section. If we're a document, we have to create
                    # one, if we're not a document something's broken and
                    # we pass controll back to the caller and let him deal
                    # with it. If we're a pages section, we create a page
                    # subsection, of course.
                    lines.rewind()
                    if issubclass(cls, document_section):
                        self.pages_section = pages_section.parse(
                            self, lines, level+1)
                    elif issubclass(cls, pages_section):
                        self.pages_section = page_section.parse(
                            self, lines, level+1)
                    else:
                        raise StopIteration

                    self.append(self.pages_section)

                elif keyword in subsection_keywords.keys():
                    # A regular subsection for ourselves.
                    subsection_cls = subsection_keywords[keyword]
                    lines.rewind()
                    self.append(subsection_cls.parse(self, lines, level+1))

                elif keyword in peer_keywords:
                    # Pass controll back to the caller.
                    raise StopIteration

                elif keyword[0] == "+" and last_comment is not None:
                    last_comment.info = "%s %s" % ( last_comment.info,
                                                    strip(line)[1:], )
                elif keyword == trailer_section.begin and \
                         not isinstance(self, document_section):
                    lines.rewind()
                    raise StopIteration

                else:
                    cmt = comment(keyword, _info=info)
                    last_comment = cmt
                    setattr(self, keyword, cmt)

                    if hasattr(parent, "header"):
                        header = parent.header
                        if hasattr(header, keyword):
                            header_cmt = getattr(header, keyword)
                            if strip(header_cmt.info) == "(atend)":
                                setattr(header, keyword, cmt)


        except StopIteration:
            pass

        # Initialize a subfile
        self.subfile = subfile(lines.fp, start_seek_pointer,
                               lines.fp.tell() - start_seek_pointer)

        print >> debug,  "<<" * level, "E", self.name()

        return self

    parse = classmethod(parse)

    def name(cls):
        return cls.__name__[:-len("_section")]
    name = classmethod(name)


class header_section(section):

    begin = None
    end = "EndComments"
    mandatory = True

    # properties that refer to document meta data
    bounding_box = parsed_property("BoundingBox", "iiii", True)
    hires_bounding_box = parsed_property("HiResBoundingBox",
                                         "ffff", True)
    creator = parsed_property("Creator", "l")
    creation_date = parsed_property("CreationDate", "l")
    document_data = parsed_property("DocumentData", "l")
    emulation = parsed_property("Emulation", "l")
    extensions = string_list_property("Extensions")
    for_ = parsed_property("For", "l", True) # for's a Py keyword!
    language_level = parsed_property("LanguageLevel", "i", True)
    orientation = parsed_property("Orientation", "l", True)
    pages = parsed_property("Pages", "i", True)
    page_order = parsed_property("PageOrder", "s", True)
    routing = parsed_property("Routing", "l", True)
    title = parsed_property("Title", "l", True)
    version = parsed_property("Version", "l", True)

    document_needed_resources = resources_property(
        "DocumentNeededResources", atend=True)
    document_supplied_resources = resources_property(
        "DocumentSuppliedResources", atend=True)

    document_needed_fonts = string_list_property("DocumentNeededFonts", True)
    document_needed_procsets = string_list_property("DocumentNeededProcSets",
                                                    True)
    document_supplied_fonts = string_list_property(
        "DocumentSuppliedFonts", True)
    document_supplied_procsets = string_list_property(
        "DocumentSuppliedProcSets", True)

    document_process_colors = string_list_property(
        "DocumentProcessColors", True)
    document_custom_colors = string_list_property(
        "DocumentCustomColors", True)

class defaults_section(section):
    begin = "BeginDefaults"
    end = "EndDefaults"

    page_bounding_box = parsed_property("PageBoundingBox", "ffff")
    page_media = parsed_property("PageMedia", "s")
    page_orientation = parsed_property("Page", "s")
    page_process_colors = string_list_property("PageProcessColors")
    page_custom_colors = string_list_property("PageCustomColors")
    page_requirements = string_list_property("PageRequirements")
    page_resources = string_list_property("PageResources")


class setup_section(section):
    begin = "BeginSetup"
    end = "EndSetup"

class prolog_section(section):
    begin = "BeginProlog"
    end = "EndProlog"
    possible_subsections = ( "resource", )

class pages_section(section):
    begin = None
    end = None
    possible_subsections = ( "page", )


class page_section(section):
    begin = "Page"
    possible_subsections = ( "pageheader", "pagesetup",
                             "document", "object",
                             "pagetrailer", )

    page_bounding_box = parsed_property("PageBoundingBox", "ffff", atend=True)
    hires_page_bounding_box = parsed_property("PageHiResBoundingBox",
                                              "ffff", atend=True)
    page_custom_colors = string_list_property("PageCustomColors", atend=True)
    page_media = parsed_property("PageMedia", "s")
    page_orientation = parsed_property("Page", "s")
    page_process_colors = string_list_property("PageProcessColors", atend=True)
    page_requirements = string_list_property("PageRequirements")
    page_resources = string_list_property("PageResources")


class pageheader_section(section):
    begin = None
    end = "EndPageComments"
    mandatory = True

class pagesetup_section(section):
    begin = "BeginPageSetup"
    end = "EndPageSetup"

class pagetrailer_section(section):
    begin = "PageTrailer"
    mandatory = True

class document_section(section):
    begin = "BeginDocument"
    end = "EndDocument"
    possible_subsections = ( "header", "defaults", "prolog", "setup",
                             "pages", "trailer", )

    def resources(self):
        """
        Return a resource_set instance containing the resources this
        document contains. This refers to actual resource sections,
        not to the DocumentSuppliedResources DSC comment refered to by
        the document_supplied_resource property above.
        """
        ret = dsc_resource_set()
        for a in self.prolog.subsections("Resource"):
            ret.append(dsc_resource.from_section(a))

        if self.has_subsection("Setup"):
            for a in self.setup.subsections("Resource"):
                ret.append(dsc_resource.from_section(a))

        return ret

    def add_resource(self, resource):
        if not resource in self.resources():
            self.prolog.append(resource.section)


class resource_section(section):
    begin = "BeginResource"
    end = "EndResource"

    def resource(self):
        return dsc_resource.from_section(self)

class trailer_section(section):
    begin = "Trailer"
    end = None

class object_section(section):
    begin = "BeginObject"
    end = "EndObject"

class pdfpage_setup_buffer(file_like_buffer):
    """
    A place to store pdf setup information for a page, that is
    TrimBox, ArtBox etc. and the required translation. This is handled in
    such a way so that rendering routines can identify and maybe remove
    the translation.
    """
    def boxtuple(self, box):
        try:
            box = float(box)
        except ValueError:
            pass

        if type(box) == FloatType:
            return ( box, box,
                     self._page.w() + box, self._page.h() + box, )
        else:
            return box

    def box_command(self, key, box):
        if box:
            tpl = (key,) + self.boxtuple(box)
            return "[ /%s [%.2f %.2f %.2f %.2f] /PAGE pdfmark\n" % tpl
        else:
            return None

    def __init__(self, page, trim=0, art=0, crop=0, bleed=0):
        file_like_buffer.__init__(self)
        self._page = page

        print >> self, "% Start pdfpage_setup_buffer", trim, art, crop, bleed

        # If there is a crop specified, enlarge the page by that much and
        # translate its contents so that from the callers perspective, our
        # page has the ‘right’ width and hight.
        trimbox = self.boxtuple(trim)
        if trimbox != (0, 0, 0, 0):
            llx, lly, urx, ury = trimbox
            page.page_bounding_box = (-llx, -lly, page.w(), page.h())
            print >> self, llx, lly, "translate % pdfpage()"
        else:
            page.page_bounding_box = (0, 0, w, h,)

        self.append(self.box_command("TrimBox", trim))
        self.append(self.box_command("ArtBox", art))
        self.append(self.box_command("CropBox", crop))
        self.append(self.box_command("BleedBox", bleed))

        print >> self, "% End pdfpage_setup_buffer"


# Document

class dsc_document(document_section, document):
    """
    Models a regular Adobe Document Structurnig Convention 3.0 complient
    PostScript document.
    """
    begin = None
    end = "EOF"

    def __init__(self, title="", info="", empty=False):
        """
        """
        section.__init__(self, info, empty)
        document.__init__(self, title)

        self._font_wrappers = {}

        if not empty:
            self.setup_section = setup_section()
            self.append("%!PS-Adobe-3.0\n")
            self.append(header_section())
            self.append(defaults_section())
            self.append(prolog_section())
            self.append(self.setup_section)
            self.pages_section = pages_section()
            self.append(self.pages_section)
            self.append(trailer_section())

            document.__init__(self, title)

            self.document_needed_resources = dsc_resource_set()
            self._embed_counter = 0

    def from_file(cls, fp):
        """
        Create a dsc_document from file pointer fp.
        """
        lines = line_iterator(fp)
        first_line = lines.next()

        ret = cls.parse(None, lines)
        ret.subfile = fp

        return ret

    from_file = classmethod(from_file)

    def from_string(cls, s):
        """
        Create a dsc_document from string s.
        """
        return cls.from_file(cStringIO(s))

    from_string = classmethod(from_string)

    def page(self, page_size="a4", label=None):
        ret = dsc_page(self, page_size, label)
        self.pages_section.append(ret)
        return ret

    def pdfpage(self, page_size="a4", label=None,
                trim=0, art=0, crop=0, bleed=0):
        """
        Return a page that is meant to be used in a document that is
        destilled to pdf. The page will have a bounding box of the
        specified `page_size` and the pdfmark operator will be used to
        define area(s) beyond the page media. The page will be translated
        so that 0,0 still refers to the lower left corner of the CropBox.

        If the crop, bleed, trim and art parameters, which refer to
        the CropBox, BleedBox, TrimBox and ArtBox respectively, are a
        float value, a box of that size will be defined arround the
        page.  If they are a 4-tuple of floats that tuple is expected
        to be coordinates of the lower left and upper right corner of
        the box as specified by the documentation on pdfmark.
        """
        w, h = parse_paper_size(page_size)

        page = dsc_page(self, page_size, label)
        page.pagesetup.append(pdfpage_setup_buffer(
                page, trim, art, crop, bleed))
        self.append(page)
        return page

    def remove_pdfpage_setup(self):
        """
        Remove pdfpage_setup instances for all pages’s pagesetup
        sections and reset the page’s boundingbox.
        """
        for index, page in enumerate(self.pages_section):
            for element in page.pagesetup:
                if isinstance(element, pdfpage_setup_buffer):
                    del page.pagesetup[index]
                    break

    def pages(self):
        return filter(lambda p: isinstance(p, dsc_page), self.pages_section)

    def output_file(self): return self

    def add_font(self, font):
        from t4.psg import procsets
        self.add_resource(procsets.dsc_font_utils)
        if isinstance(font, type1):
            if font.main_font_file() is None:
                self.document_needed_resources.append(
                    dsc_resource("font", font.ps_name) )
            else:
                resource_name = "font %s" % font.ps_name

                if not self.prolog.has_subsection("resource", resource_name):
                    fp = font.main_font_file()
                    fp.seek(0)
                    first_line = fp.read(30)
                    first_byte = ord(first_line[0])
                    fp.seek(0)

                    if first_byte == 128: # pfb
                        font_file = pfb2pfa_buffer(fp)
                    else:
                        if not first_line.startswith("%!PS-AdobeFont"):
                            raise NotImplementedError("Not a pfa/b file!")
                        else:
                            font_file = file_as_buffer(fp)

                    section = resource_section(info=resource_name)
                    section.append(font_file)
                    self.prolog.append(section)
        else:
            raise NotImplementedError("Fonts other than Type1")

    def register_font(self, font):
        """
        This function will register a font with this document and
        return a font_wrapper object, see document.py.
        """
        if not self._font_wrappers.has_key(font.ps_name):
            number_of_fonts = len(self._font_wrappers)
            self.add_font(font)
            wrapper = font_wrapper(self, -number_of_fonts, font, True)
            self.setup_section.append(wrapper)
            self._font_wrappers[font.ps_name] = wrapper

        return self._font_wrappers[font.ps_name]


    def name(cls):
        return "dsc_document"
    name = classmethod(name)

    def write_to(self, fp):
        self.header.document_needed_resources = self.document_needed_resources
        self.header.document_supplied_resources = self.resources()

        document_section.write_to(self, fp)

    def embed_counter(self):
        self._embed_counter += 1
        return self._embed_counter

    def file_resource(self, file_id):
        ret = resource_section(info = "file (%s)" % file_id)
        self.prolog.append(ret)
        return ret

    class custom_color(document.custom_color):
        def __init__(self, _document, name, colspec):
            document.custom_color(_document, name, colspec)

            if self.document.language_level is None or \
                   self.document.language_level < 2:
                self.document.language_level = 2

            if self.name not in self.document.document_custom_colors:
                self.document.document_custom_colors.append(self.name)

        def __str__(self):
            return self.setcolor(1)

        def setcolor(self, opacity):
            """
            @param opacity: Indicate how much ink of the this color is to
               be put on the page. 0 means none at all and 1 means full
               throttle.
            """
            # The way this is handled comes from pslib by
            # Vilson Gärtner and Uwe Steinmann.

            ret = []
            ret.append("[ /Separation %s" % ps_escape(self.name))

            if len(self.colspec) == 1:
                ret.append("  /DeviceGray { 1 %f sub mul 1 exch sub }" % \
                                                                self.colspec)
            elif len(self.colspec) == 3:
                m = max(*self.colspec)
                tpl = ( m, self.colspec[0],
                        m, self.colspec[1],
                        m, self.colspec[2], )

                ret.append(("  /DeviceRGB { 1 exch sub dup dup "
                            "%f exch sub %f mul add exch dup dup "
                            "%f exch sub %f mul add exch dup "
                            "%f exch sub %f mul add }") % tpl)

            elif len(self.colspec) == 4:
                ret.append(("  /DeviceCMYK { dup %f mul exch dup %f mul exch "
                            "dup %f mul exch %f mul }") % self.colspec)

            ret.append("] setcolorspace")
            ret.append("%f setcolor", opacity)

            return join(ret, "\n")


class dsc_page(page, page_section):
    def __init__(self, document, page_size="a4", label=None, ordinal=None):
        page.__init__(self, document, page_size, label, ordinal)

        info = "%s %i" % ( ps_escape(self.label), self.ordinal)
        page_section.__init__(self, info=info)

        self.append(pagesetup_section())
        self.trailer = pagetrailer_section()

    def write_to(self, fp):
        print >> fp, "%%Page:", self.info
        file_like_buffer.write_to(self, fp)
        print >> fp, "showpage"
        self.trailer.write_to(fp)

    def register_font(self, font, document_level=True):
        if self._font_wrappers.has_key(font.ps_name):
            return self._font_wrappers[font.ps_name]
        else:
            ret = page.register_font(self, font, document_level=True)
            if document_level: self.document.add_font(font)
            return ret

    def canvas(self, margin=0, border=False, clip=False):
        ret = page.canvas(self, margin, border, clip)
        self.append(ret)

        return ret

class eps_document(dsc_document):
    """
    An EPS document is a DSC document with a small number of
    restrictios.  The most important of which is that it contains only
    one page which is not flushed using showpage. Also a BoundingBox
    DSC comment in the document header is mandetory. The others can be
    summarized in 'do what you would for a cleanly structured DSC
    document' and 'avoid certain operators'. The details may be found
    in the 'Encapsulated PostScript File Format Specification'
    available from Adobe.

    The technical difference between dsc_document above and
    eps_document is that eps_document does not own a pages section,
    but a single page section directly in the document (Except when it
    is read from dist. Reading works exactly the same as for any DSC
    document!)

    The only rule from the specification enforced by this class is the
    presence of a BoundingBox DSC comment in the document's header
    section.
    """
    def __init__(self, title="", info="", empty=False):
        section.__init__(self, info, empty=True)
        document.__init__(self, title)

        if not empty:
            self.append("%!PS-Adobe-3.0 EPSF-3.0\n")
            self.append(header_section())
            self.append(defaults_section())
            self.append(prolog_section())
            self.setup_section = setup_section()
            self.append(self.setup_section)

            # For convenience an eps document still contains a pages section
            # aliasing the single page it contains.
            page = eps_page(self)
            self.pages_section = pages = pages_section()
            pages.append(page)
            self.append(pages)

            self.page = page # this will overwrite dsc_document's  page()
                             # function which we don't need in an EPS document
                             # since it only has one page.

            self.append(trailer_section())

            document.__init__(self, title)

            self.document_needed_resources = dsc_resource_set()
            self._embed_counter = 0

            self._font_wrappers = {}

    def write_to(self, fp):
        found = False
        for cmt in self.header.comments():
            if cmt.name == "BoundingBox": found = True

        if not found:
            raise CommentMissing( ("An EPS file's header must contain a "
                                   "BoundingBox comment.") )

        dsc_document.write_to(self, fp)

class eps_page(dsc_page):
    """
    This class is exactly the same as dsc_page above, except that it
    does not write a showpage operator at the end of a page.s
    """

    def write_to(self, fp):
        """
        The write_to() method has been overloaded to prevent that a
        showpage operater is added to the page as required by the EPS
        specifications.
        """
        print >> fp, "%%Page:", self.info
        file_like_buffer.write_to(self, fp)
        self.trailer.write_to(fp)
