#!/usr/bin/python

##  This file is part of psg, PostScript Generator.
##
##  Copyright 2006–23 by Diedrich Vorberg <diedrich@tux4web.de>
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

import collections.abc, functools

from .base import PSBuffer, encode
from .utils import ps_escape
from .measure import has_dimensions, parse_size

def ps_literal(value) -> bytes:
    """
    Convert Python primitive into a DSC literal. This will use
    Python's str() function on the value, because it produces ideal
    results for integer and float values. Strings will be quoted
    according to the DSC's rules as layed out in the specifications on
    page 36 (section 4.6, on <text>).
    """
    if type(value) in ( str, bytes ):
        return ps_escape(value, False)
    else:
        return encode(str(value))


class Comment(object):
    """
    A DSC comment, starting with %% and contains `args`.
    """
    def __init__(self, keyword:str, value=None):
        self.keyword = keyword
        self.set(value)

    def set(self, value):
        self._value = value

        if value is None:
            self._payload = None
        elif type(self._value) in (str, bytes, int, float):
            self._payload = ps_literal(value)
        elif isinstance(value, collections.abc.Sequence):
            self._payload = b" ".join([ ps_literal(a) for a in value ])
        else:
            raise TypeError("Can’t handle " + repr(value))

    @property
    def value(self):
        return self._value

    def __bytes__(self):
        if self._value is None:
            return b"%%" + encode(self.keyword) + b"\n"
        elif self.keyword == b"+":
            return b"%%+ " + self._payload + b"\n"
        else:
            return b"%%" + encode(self.keyword) + b": " + self._payload + b"\n"

    def __repr__(self):
        return (f"<{self.__class__.__name__} {self.keyword}={self.value} "
                f"{repr(self._payload)}")

class CommentProperty(property):
    def __init__(self, comment_keyword):
        self.comment_keyword = comment_keyword

    def __get__(self, section, owner=None):
        if section.has_comment(self.comment_keyword):
            return section.comment(self.comment_keyword).value
        else:
            return None

    def __set__(self, section, value):
        section.set_comment_value(self.comment_keyword, value)

class CommentListProperty(CommentProperty):
    def __get__(self, section, owner=None):
        ret = CommentProperty.__get__(self, section, owner)
        if ret is None:
            ret = []
            self.__set__(section, ret)

        return ret


class Default(object): pass

class CommentCache(dict):
    def __init__(self, *initial_comments):
        dict.__init__(self)

        for comment in initial_comments:
            self.add(comment)

    def add(self, comment:Comment):
        self[comment.keyword] = comment

    def __contains__(self, key):
        return dict.__contains__(self, key)

    def __getitem__(self, key):
        return dict.__getitem__(self, key)

    def get(self, key, default=Default):
        ret = dict.get(self, key, default)
        if ret is Default:
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

class DSCBuffer(PSBuffer):
    def __init__(self, *things):
        self.parent = None
        super().__init__(*things)

    def write(self, *things):
        for thing in things:
            if isinstance(thing, DSCBuffer):
                thing.parent = self
                thing.on_parent_set()

        super().write(*things)

    def on_parent_set(self):
        pass

    def walk_up_to(self, buffer_class, default=Default):
        here = self
        while True:
            if isinstance(here, buffer_class):
                return here
            here = here.parent
            if here is None:
                if default is not Default:
                    return default
                else:
                    raise AttributeError()

    @functools.cached_property
    def document(self):
        """
        Walk up the section tree and return the document.
        Return None if not in the tree (yet).
        """
        return self.walk_up_to(Document)

    @functools.cached_property
    def page(self):
        """
        Walk up the section tree and return the page we’re on.
        Return None if not in the tree (yet) or not the right
        section to ask for a page.
        """
        return self.walk_up_to(Page)


class Section(DSCBuffer):
    """
    Abstract class.

    Model a section of a postscript document. A section is a DSCBuffer that
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

          Prolog -- section
             Resource0
             Resource1
             ...

          Setup -- section

          Pages -- section

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
    """
    def __init__(self, keyword=None, has_end=False):
        """
        The arguments passed will be put into the beginning comment.
        Remains unused if `begin_keyword` is None.
        """
        super().__init__()

        if keyword is None:
            self.keyword = self.__class__.__name__.replace("Section", "")
        else:
            self.keyword = keyword
        self.has_end = has_end

        self._comment_cache = CommentCache()
        self._subsection_cache = SectionCache()

        self.write(self.begin_comment())

    def begin_comment(self):
        return Comment("Begin" + self.keyword)

    def end_comment(self):
        return Comment("End" + self.keyword)

    def write(self, *things):
        for thing in things:
            if isinstance(thing, Comment):
                self._comment_cache.add(thing)
            elif isinstance(thing, Section):
                self._subsection_cache.add(thing)

        super().write(*things)

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
            return self._subsection_cache.copy()
        else:
            return self._subsection_cache.by_name(name)

    def write_to(self, fp):
        super().write_to(fp)

        end_comment = self.end_comment()
        if end_comment:
            fp.write(bytes(end_comment))

    def __repr__(self):
        return "<%s %s (%i subsections)>" % (
            self.__class__.__name__,
            self.name,
            len(list(self.subsections())),)


    @property
    def name(self):
        return self.__class__.__name__[:-len("Section")]


class DocumentSuppliedResourceComments(DSCBuffer):
    def write_to(self, fp):
        tmpbuf = PSBuffer()
        first = True
        for resource in self.document.prolog.resources():
            if first:
                keyword = "DocumentSuppliedResources"
                first = False
            else:
                keyword = "+"

            tmpbuf.append(Comment(keyword, resource.begin_comment().value))

        tmpbuf.write_to(fp)


class HeaderSection(Section):
    """
    Header section of a DSC complient PostScript document
    """
    def __init__(self):
        super().__init__()

        self.append(DocumentSuppliedResourceComments())

    def begin_comment(self):
        return None

    def end_comment(self):
        return Comment("EndComments")

    # properties that refer to document meta data
    bounding_box = CommentProperty("BoundingBox")
    hires_bounding_box = CommentProperty("HiResBoundingBox")
    creator = CommentProperty("Creator")
    creation_date = CommentProperty("CreationDate")
    document_data = CommentProperty("DocumentData")
    emulation = CommentProperty("Emulation")
    extensions = CommentListProperty("Extensions")
    for_ = CommentProperty("For")
    language_level = CommentProperty("LanguageLevel")
    orientation = CommentProperty("Orientation")
    pages = CommentProperty("Pages")
    page_order = CommentProperty("PageOrder")
    routing = CommentProperty("Routing")
    title = CommentProperty("Title")
    version = CommentProperty("Version")

    # document_needed_fonts = CommentListProperty("DocumentNeededFonts")
    # document_needed_procsets = CommentListProperty("DocumentNeededProcSets")
    # document_supplied_fonts = CommentListProperty("DocumentSuppliedFonts")
    # document_supplied_procsets = CommentListProperty("DocumentSuppliedProcSets")

    # document_process_colors = CommentListProperty("DocumentProcessColors")
    # document_custom_colors = CommentListProperty("DocumentCustomColors")


class DefaultsSection(Section):
    page_bounding_box = CommentProperty("PageBoundingBox")
    page_media = CommentProperty("PageMedia")
    page_orientation = CommentProperty("PageOrientation")
    page_process_colors = CommentListProperty("PageProcessColors")
    page_custom_colors = CommentListProperty("PageCustomColors")
    page_requirements = CommentListProperty("PageRequirements")
    page_resources = CommentListProperty("PageResources")

class SetupSection(Section):
    pass

class PrologSection(Section):
    def resources(self):
        for thing in self._things:
            if isinstance(thing, ResourceSection):
                yield thing

class PseudoSection(Section):
    """
    Section without Begin and End comments
    """
    def begin_comment(self):
        pass

    def end_comment(self):
        pass

class PagesSection(PseudoSection):
    def append(self, thing):
        assert isinstance(thing, PageBase), TypeError
        self.document.header.pages = len(self._things)
        return super().append(thing)

class PDFPageSetup(PseudoSection):
    """
    A place to store pdf setup information for a page, that is
    TrimBox, ArtBox etc. and the required translation. This is handled in
    such a way so that rendering routines can identify and maybe remove
    the translation.
    """
    def boxtuple(self, box):
        return ( box, box, self.page.w + box, self.page.h + box, )

    def box_command(self, key, box):
        if box:
            tpl = (key,) + self.boxtuple(box)
            return "[ /%s [%.2f %.2f %.2f %.2f] /PAGE pdfmark\n" % tpl
        else:
            return None

    def __init__(self, trim=0, art=0, crop=0, bleed=0):
        PseudoSection.__init__(self)

        self.trim, self.art, self.crop, self.bleed = trim, art, crop, bleed

    def on_parent_set(self):
        self.print("% Start pdfpage_setup_buffer",
                   self.trim, self.art, self.crop, self.bleed)

        # If there is a crop specified, enlarge the page by that much and
        # translate its contents so that from the callers perspective, our
        # page has the ‘right’ width and hight.
        trimbox = self.boxtuple(self.trim)
        if trimbox[:2] != (0, 0, 0, 0):
            llx, lly, urx, ury = trimbox
            self.page.bounding_box = (-llx, -lly,
                                      self.page.w, self.page.h)
            if llx != 0 or lly != 0:
                self.print(llx, lly, "translate % pdfpage()")

        self.append(self.box_command("TrimBox", self.trim))
        self.append(self.box_command("ArtBox", self.art))
        self.append(self.box_command("CropBox", self.crop))
        self.append(self.box_command("BleedBox", self.bleed))

        self.print("% End pdfpage_setup_buffer")


class PageBase(Section, has_dimensions):
    """
    Common base class for Page and EPSPage below.
    """
    bounding_box = CommentProperty("PageBoundingBox")
    hires_bounding_box = CommentProperty("PageHiResBoundingBox")
    custom_colors = CommentListProperty("PageCustomColors")
    media = CommentProperty("PageMedia")
    orientation = CommentProperty("Page")
    process_colors = CommentListProperty("PageProcessColors")
    requirements = CommentListProperty("PageRequirements")
    resources = CommentListProperty("PageResources")

    def __init__(self, size="a4", source_comment=None):
        self.source_comment = source_comment

        Section.__init__(self, None, False)
        has_dimensions.__init__(self, *parse_size(size))

        self.header = self.append(PageHeaderSection())
        self.setup = self.append(PageSetupSection())
        self.trailer = self.append(PageTrailerSection())

        self.bounding_box = (0, 0, self.w, self.h,)

    def begin_comment(self):
        return Comment("Page", self.source_comment)

    def end_comment(self):
        return None

class Page(PageBase):
    """
    The default page will flush everything drawn with the showpage operator.
    """
    def __init__(self, size="a4", source_comment=None,
                 trim=0, art=0, crop=0, bleed=0):
        super().__init__(size, source_comment)
        self.setup.append(PDFPageSetup(trim, art, crop, bleed))

    def write_to(self, fp):
        super().write_to(fp)
        fp.write(b"showpage\n")

class EPSPage(PageBase):
    """
    EPS Documents may not include the showpage operator.
    """
    pass

class PageHeaderSection(Section):
    """
    Header section of a DSC complient PostScript document
    """
    def begin_comment(self):
        return None

    def end_comment(self):
        return Comment("EndPageComments")

class PageSetupSection(Section):
    pass

class PageTrailerSection(Section):
    has_end = False


class ResourceSection(Section):
    def __init__(self, type, *info):
        self.type = type
        self.info = info
        super().__init__(has_end=True)

    def begin_comment(self):
        cmt = super().begin_comment()
        cmt.set( (self.type,) + self.info )
        return cmt

    def __eq__(self, other):
        return (self.type == other.type and self.info == other.info)

class Trailer(Section):
    has_end = False

class Object(Section):
    pass


class Document(Section):
    def __init__(self):
        super().__init__(None, True)

        self._embed_counter = 0

        self.header = self.append(HeaderSection())
        self.defaults = self.append(DefaultsSection())
        self.prolog = self.append(PrologSection())
        self.setup = self.append(SetupSection())
        self.pages = self.append(PagesSection())
        self.trailer = self.append(Trailer())

    def begin_comment(self):
        return b"%!PS-Adobe-3.0\n"

    def end_comment(self):
        return Comment("EOF")

    def new_embed_number(self):
        self._embed_counter += 1
        return self._embed_counter

    def add_resource(self, resource):
        if resource not in self.prolog.resources():
            self.prolog.append(resource)

    def append(self, thing):
        if isinstance(thing, PageBase):
            return self.pages.append(thing)
        else:
            return super().append(thing)

class EPSDocument(Document):
    """
    An EPS document is a DSC document with a small number of
    restrictios.  The most important of which is that it contains only
    one page which is not flushed using showpage. Also a BoundingBox
    DSC comment in the document header is mandetory. The others can be
    summarized in 'do what you would for a cleanly structured DSC
    document' and 'avoid certain operators'. The details may be found
    in the 'Encapsulated PostScript File Format Specification'
    available from Adobe.

    An EPSDocument instance is initialized with a page size and the
    document’s one page of that size is available throug the `page`
    attribute.

    The only rule from the specification enforced by this class is the
    presence of a BoundingBox DSC comment in the document's header
    section.
    """
    def __init__(self,
                 pagesize="a4",
                 # From Page’s constructor:
                 source_comment=None):
        super().__init__()
        self.page = self.append(EPSPage(pagesize, source_comment))

        self.header.bounding_box = self.page.bounding_box

    def begin_comment(self):
        return b"%!PS-Adobe-3.0 EPSF-3.0\n"
