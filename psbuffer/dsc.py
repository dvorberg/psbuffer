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
from collections import namedtuple

from .base import PSBuffer, encode, ps_literal
from .measure import has_dimensions, parse_size

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

    def write_to(self, fp):
        if self._value is None:
            fp.write(b"%%" + encode(self.keyword) + b"\n")
        elif self.keyword == b"+" or self.keyword == "+":
            fp.write(b"%%+ " + self._payload + b"\n")
        else:
            fp.write(b"%%" + encode(self.keyword) + b": " + \
                     self._payload + b"\n")

    def __repr__(self):
        return (f"<{self.__class__.__name__} {self.keyword}={self.value} "
                f"{repr(self._payload)}")


class LazyComment(Comment):
    def __init__(self, keyword, callback):
        super().__init__(keyword, None)
        self._callback = callback

    @property
    def value(self):
        raise NotImplemented()

    def write_to(self, fp):
        self.set(self._callback())
        return super().write_to(fp)

class _BoundingBoxCommentBase(Comment):
    def __init__(self, keyword, numeric_type, container, value=None):
        self.container = container
        self.numeric_type = numeric_type

        if isinstance(container, PageBase):
            keyword = "Page" + keyword

        super().__init__(keyword, value)

    def set(self, value):
        if hasattr(self.container, "calculate_bounding_box"):
            if value is not None:
                raise AttributeError("The BoundBox of this container is "
                                     "calculated by calculate_bounding_box().")
        else:
            self.container.__bounding_box = value

    @property
    def value(self):
        if hasattr(self.container, "calculate_bounding_box"):
            return self.container.calculate_bounding_box()
        else:
            return self.container.__bounding_box

    def write_to(self, fp):
        value = self.value

        if value is None:
            pass
        else:
            value = [ ps_literal(self.numeric_type(c)) for c in value ]
            fp.write(b"%%" + encode(self.keyword) + b": " + \
                     b" ".join(value) + b"\n")

class BoundingBoxComment(_BoundingBoxCommentBase):
    def __init__(self, container, value=None):
        super().__init__("BoundingBox", int, container, value)

class HiResBoundingBoxComment(_BoundingBoxCommentBase):
    def __init__(self, container, value=None):
        super().__init__("HiResBoundingBox", float, container, value)

class CommentProperty(property):
    def __init__(self, comment_keyword):
        self.comment_keyword = comment_keyword

    def __get__(self, section, owner=None):
        if self.comment_keyword in section.property_comments:
            return section.property_comments[self.comment_keyword].value
        else:
            raise AttributeError(self.comment_keyword)

    def __set__(self, section, value):
        if not self.comment_keyword in section.property_comments:
            section.property_comments.add(Comment(self.comment_keyword, value))
        else:
            section.property_comments[self.comment_keyword].set(value)


class CommentListProperty(CommentProperty):
    def __get__(self, section, owner=None):
        ret = CommentProperty.__get__(self, section, owner)
        if ret is None:
            ret = []
            self.__set__(section, ret)

        return ret


class Default(object): pass


class CommentCache(dict):
    def __init__(self, container, *initial_comments):
        dict.__init__(self)
        self.container = container

        for comment in initial_comments:
            self.add(comment)

    def add(self, comment:Comment):
        if comment.keyword in self:
            raise KeyError(f"A {comment.keyword} already exists.")

        self[comment.keyword] = comment
        self.container.append(comment)

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
        return self.walk_up_to(PageBase)



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
    def __init__(self, keyword=None, has_end=False, initial_comments=[]):
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

        self.property_comments = CommentCache(self, *initial_comments)
        self.subsection_cache = SectionCache()

        self.write(self.begin_comment())

    def begin_comment(self):
        return Comment("Begin" + self.keyword)

    def end_comment(self):
        return Comment("End" + self.keyword)

    def write(self, *things):
        for thing in things:
            if isinstance(thing, Section):
                self.subsection_cache.add(thing)

        super().write(*things)

    # Subsection management
    def has_subsection(self, name):
        """
        Determine whether this section contains a subsection by that name.
        """
        return name in self.subsection_cache

    def subsections(self, name=None):
        """
        Return an iterator over of this sections subsections.

        @param name: Return only those subsections whoes name is 'name'.
        """
        if name is None:
            return self.subsection_cache.copy()
        else:
            return self.subsection_cache.by_name(name)

    def write_to(self, fp):
        super().write_to(fp)

        end_comment = self.end_comment()
        if end_comment:
            end_comment.write_to(fp)

    def __repr__(self):
        return "<%s %s (%i subsections)>" % (
            self.__class__.__name__,
            self.name,
            len(list(self.subsections())),)


    @property
    def name(self):
        return self.__class__.__name__[:-len("Section")]


class DocumentSuppliedResourcesComment(DSCBuffer):
    def __init__(self, document):
        super().__init__()
        self.document = document

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

NeededResource = namedtuple("NeededResource", [ "type", "identifyer", ])

class DocumentNeededResourcesComment(DSCBuffer):
    def __init__(self, document):
        super().__init__()
        self.document = document

    def write_to(self, fp):
        tmpbuf = PSBuffer()
        first = True
        for type, identifyer in self.document.needed_resources:
            if first:
                keyword = "DocumentNeededResources"
                first = False
            else:
                keyword = "+"

            tmpbuf.append(Comment(keyword, [type, identifyer,]))

        tmpbuf.write_to(fp)


class HeaderSection(Section):
    """
    Header section of a DSC complient PostScript document
    """
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

    #process_colors = CommentListProperty("DocumentProcessColors")
    #custom_colors = CommentListProperty("DocumentCustomColors")


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
        return super().append(thing)

    def ordinal_of(self, page):
        assert isinstance(page, PageBase), TypeError
        # Things starts with b'' so the index of the pages
        # is 1-based.
        return self._things.index(page)

    @property
    def page_objects(self):
        return self._things[1:]

    def __len__(self):
        return len(self.page_objects)

    def __getitem__(self, idx):
        return self.page_objects[idx]

    def __iter__(self):
        return iter(self.page_objects)

    @property
    def page_count(self):
        # self._things[0] == b"" !
        return len(self._things) - 1

    def __iter__(self):
        for page in self._things[1:]:
            yield page

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
            self.page.bounding_box = (-llx, -lly, self.page.w, self.page.h)
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

    def __init__(self, size="a4", label=None):
        self.label = label

        Section.__init__(self, None, False)
        has_dimensions.__init__(self, *parse_size(size))

        self.header = self.append(PageHeaderSection())
        self.property_comments = self.header.property_comments

        self.property_comments.add(BoundingBoxComment(self))
        self.property_comments.add(HiResBoundingBoxComment(self))

        self.setup = self.append(PageSetupSection())
        self.trailer = self.append(PageTrailerSection())

        # Make sure the page has a bounding_box.
        self.bounding_box = (0, 0, self.w, self.h,)

    def begin_comment(self):
        return LazyComment("Page", self.begin_comment_value)

    def begin_comment_value(self):
        ordinal = self.ordinal
        return ( self.label or ordinal, ordinal, )

    @functools.cached_property
    def ordinal(self):
        return self.document.pages.ordinal_of(self)

    def end_comment(self):
        return None

class Page(PageBase):
    """
    The default page will flush everything drawn with the showpage operator.
    """
    def __init__(self, size="a4", label=None,
                 trim=0, art=0, crop=0, bleed=0):
        super().__init__(size, label)
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
        super().__init__(keyword="Resource", has_end=True)

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
        self.property_comments = self.header.property_comments

        self.property_comments.add(
            LazyComment("Pages", lambda: self.pages.page_count))
        self.property_comments.add(BoundingBoxComment(self))
        self.property_comments.add(HiResBoundingBoxComment(self))

        self.header.append(DocumentNeededResourcesComment(self))
        self.header.append(DocumentSuppliedResourcesComment(self))
        #self.header.process_colors = []
        #self.header.custom_colors = []

        self.defaults = self.append(DefaultsSection())
        self.prolog = self.append(PrologSection())
        self.setup = self.append(SetupSection())
        self.pages = self.append(PagesSection())
        self.trailer = self.append(Trailer())

        self.needed_resources = set()
        self._font_encodings = {}

    def get_encoding_for(self, font):
        if not font.ps_name in self._font_encodings:
            font.add_to(self)
            self._font_encodings[font.ps_name] = font.make_encoding(self)

        return self._font_encodings[font.ps_name]

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

    def calculate_bounding_box(self):
        pages = self.pages.page_objects

        if len(self._things) > 0:
            llx, lly, urx, ury = pages[0].bounding_box

            for page in pages[1:]:
                a, b, c, d = page.bounding_box
                if a < llx: llx = a
                if b < lly: lly = b
                if c > urx: urx = c
                if d > ury: ury = d

            return (llx, lly, urx, ury,)
        else:
            return None

    def add_needed_resource(self, type, identifyer):
        assert type in ("file", "font", "procset",), ValueError
        self.needed_resources.add(NeededResource(type, identifyer))

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
    def __init__(self, pagesize="a4"):
        super().__init__()
        self.page = self.append(EPSPage(pagesize, None))

    def begin_comment(self):
        return b"%!PS-Adobe-3.0 EPSF-3.0\n"
