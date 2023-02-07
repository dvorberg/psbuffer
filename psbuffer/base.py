#!/usr/bin/python

##  This file is part of psbuffer.
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

import os, io

STRING_ENCODING="utf-8"

# For my development process.
debug = print

def encode(s):
    if type(s) is str:
        return s.encode(STRING_ENCODING)
    else:
        return s

class PSBuffer(object):
    """
    Contain PostScript source as byte-strings and other psbuffer objects
    to be written to a file (which must be in binary mode). All methods
    also accept strings as input, which will be converted to bytes.
    """
    def __init__(self, *things):
        self._things = list()
        self.write(*things)

    def _convert(self, thing):
        if type(thing) is bytes or hasattr(thing, "write_to"):
            return thing
        elif hasattr(thing, "__bytes__"):
            return bytes(thing)
        elif thing is None:
            return b""
        else:
            return bytes(str(thing).encode(STRING_ENCODING))

    def write(self, *things):
        self._things += [ self._convert(thing) for thing in things ]

    def append(self, thing):
        self.write(thing)
        return thing

    def prepend(self, *things):
        for thing in things:
            self._things.insert(0, self._convert(thing))

    def print(self, *args, sep=b" ", end=b"\n"):
        """
        This works just like print() except that it will accept everything
        write() does and does what one would expect.
        """
        if args:
            for a in args[:-1]:
                self.write(a)
                if sep:
                    self.write(sep)

            self.write(args[-1])

            if end:
                self.write(end)

    def write_to(self, fp):
        """
        `fp` must be in binary mode.
        """
        for thing in self._things:
            if hasattr(thing, "write_to"):
                thing.write_to(fp)
            elif thing is None:
                pass
            else:
                fp.write(thing)

class FileAsBuffer(object):
    def __init__(self, fp):
        """
        `fp`: File object (in binary mode)
        """
        self.fp = fp

    def write_fo(self, fp):
        # Make sure the file pointer is at the desired position,
        # that is, the one, we were initialized with.

        while True:
            s = self.fp.read(1024)

            if s == "":
                break
            else:
                fp.write(s)

def Subfile(fp, offset, length):
    """
    This is a funny thing: A subfile class knows a file, an offset
    and a length. It implements the file interface as described in the
    Python Library Reference. It will emulate a file whoes first byte
    is the byte of the 'parent' file pointed to by the offset and
    whoes length is the provided length. After each of the calls to
    one of its functions, the 'parent' file's file pointer will be
    restored to its previous position.

    This function will return a FilesystemSubfile instance if the
    provided file pointer is a regular file and a DefaultSubfile if
    it is not.

    Tested on files in binary mode only.
    """
    if isinstance(fp, io.BytesIO):
        return BytesIOSubfile(fp, offset, length)
    else:
        try:
            fp.fileno
            return FilesystemSubfile(fp, offset, length)
        except io.UnsupportedOperation:
            raise NotImplementedError("DefaultSubfile is as of yet untested.")
            # return DefaultSubfile(fp, offset, length)

class _Subfile(object):
    def __init__(self, fp, offset, length):
        self.parent = fp
        self.offset = offset
        self.length = length

        self.seek(0)

    def close(self):
        pass

    def flush(self):
        self.parent.flush()

    def isatty(self):
        return False

    def next(self):
        raise NotImplementedError("The subfile class dosn't support iteration "
                                  "use readlines() below!")

    def read(self, bytes=None):
        if bytes is None: bytes = self.length

        if self.parent.tell() + bytes > self.offset + self.length:
            bytes = self.offset + self.length - self.parent.tell()

        if bytes < 1:
            return ""
        else:
            return self.parent.read(bytes)

    def readline(self, size=None):
        old_pos = self.parent.tell()
        line = self.parent.readline()
        if self.parent.tell() > self.offset + self.length:
            too_many = self.parent.tell() - (self.offset + self.length)
            return line[:-too_many]
        else:
            return line

    def readlines(self, sizehint=80):
        old_tell = self.parent.tell()
        bytes_read = 0
        for line in self.parent.readlines():
            bytes_read += len(line)
            if old_tell + bytes_read > self.offset + self.length:
                too_many = (old_tell+ bytes_read) - (self.offset + self.length)
                yield line[:-too_many]
                break
            else:
                yield line


    def seek(self, offset, whence=0):
        if whence == 0:
            if offset < 0: raise IOError("Can't seek beyond file start")
            self.parent.seek(self.offset + offset, 0)
        elif whence == 1:
            if self.parent.tell() - offset < 0:
                raise IOError("Invalid argument (seek beyond file start)")
            self.parent.seek(offset, 1)
        elif whence == 2:
            self.parent.seek(self.offset + self.length + offset, 0)
        else:
            raise IOError("Invalid argument (don't know how to seek)")

    def tell(self):
        return self.parent.tell() - self.offset

    def truncate(self):
        raise NotImplementedError("subfile does not implement truncate!")

    def write(self, s):
        """
        This will happily overwrite the subfile's end into whatever it
        will find there. It will reset the file pointer to the end of
        the subfile if that happens.
        """
        raise NotImplemetedError("Can’t write into subfiles.")

    def write_to(self, fp):
        self.seek(0)
        while True:
            r = self.read(1024)
            if len(r) == 0:
                break
            else:
                fp.write(r)


class FilesystemSubfile(_Subfile):
    def __init__(self, fp, offset, length):
        if not hasattr(fp, "fileno"):
            raise ValueError("A FilesystemSubfile must always be used with "
                             "a regular file, owning a fileno() method")

        parent = os.fdopen(os.dup(fp.fileno()), "br")
        if isinstance(fp, self.__class__):
            _Subfile.__init__(self, parent, offset+fp.offset, length)
        else:
            _Subfile.__init__(self, parent, offset, length)


    def fileno(self):
        return self.parent.fileno()

class DefaultSubfile(_Subfile):
    def __init__(self, fp, offset, length):
        _Subfile.__init__(self, fp, offset, length)

    def save(self):
        self.parent_seek_pointer = self.parent.tell()
        self.parent.seek(self.offset + self.seek_pointer)

    def restore(self):
        self.seek_pointer = self.parent.tell() - self.offset
        self.parent.seek(self.parent_seek_pointer)

    def read(self, size=None):
        self.save()
        return _Subfile.read(self, size)
        self.restore()

    def readline(self, size):
        self.save()
        return _Subfile.readline(self, size)
        self.restore()

    def readlines(self, size):
        self.save()
        for line in _Subfile.readlines(self, size):
            yield line
        self.restore()

    def seek(self, offset, whence=0):
        if whence == 0:
            self.seek_pointer = offset
        elif whence == 1:
            self.seek_pointer += offset
        elif whence == 2:
            self.seek_pointer = self.length + offset
        else:
            raise IOError("Invalid argument (don't know how to seek)")

    def tell(self):
        return self.seek_pointer


class BytesIOSubfile:
    def __init__(self, fp, offset, length):
        self.fp = io.BytesIO(fp.getvalue()[offset:offset+length])

    def write_to(self, fp):
        fp.write(self.fp.getvalue())

    def __getattr__(self, name):
        return getattr(self.fp, name)

class FileWrapper(object):
    def __init__(self, fp):
        self.fp = fp

    def write_to(self, fp):
        while True:
            r = self.fp.read(1024)
            if not r:
                break
            else:
                fp.write(r) # .replace(b"\r", b"\n")

class Font:
    """
    Abstract base class for fonts.
    """
    def __init__(self, ps_name, full_name, family_name,
                 weight, italic, fixed_width, metrics):
        """
        All these params become instance variables.

        @param ps_name: PostscriptIdentifyer for this font
        @param full_name: Human readable name
        @param family_name: The font family's name
        @param weight: Font weight as a string (Regular, Bold, SemiBold etc)
        @param italic: Boolean indicating whether this font is italic
        @param fixed_width: Boolean indicating whether this font has a fixed
           character width
        @param matrics: An instance of psg.font.metrics containing the font
           metrics.
        """
        self.ps_name = ps_name
        self.full_name = full_name
        self.family_name = family_name
        self.weight = weight
        self.italic = italic
        self.fixed_width = fixed_width

        self.metrics = metrics

    def has_char(self, codepoint):
        return self.metrics.has_key(codepoint)

class GlyphMetric:
    def __init__(self, char_code, width, ps_name, bounding_box):
        """
        @param char_code: Character code in font encoding
        @param width: Character width in 1/1000th unit
        @param ps_name: PostScript character name. May be None.
        @param bounding_box: Charachter bounding box in 1/1000th unit
        """
        self.char_code = char_code
        self.ps_name = ps_name
        self.width = width
        self.bounding_box = bounding_box

    def __repr__(self):
        return "<%s code=%i width=%f ps_name=%s>" % (
            self.__class__.__name__, self.font_character_code,
            self.width, self.ps_name, )


class FontMetrics(dict):
    """
    Base class for font metric calculaions. Metrics objects are
    dict that map unicode codepoints (integers) to glyph_metric
    objects. The class provides a special mechanism for accessing
    calculated attributes, see __getattr__() below.

    @ivar kerning_pairs: Dict object mapping tuples of integer (unicode
      codes) to floats (kerning value for that pair).
    """
    def __init__(self):
        self.kerning_pairs = {}
        self.kerning_pairs.setdefault(0.0)

    # def __getattr__(self, name):
    #     """
    #     The getattr will check, if there's a method called _name(). If
    #     so it will be invoked and the result stored as an attribute
    #     called name for later usage. This may copy the entire metrics
    #     from the parsed representation into this object's namespace.
    #     """
    #     if hasattr(self, "_" + name):
    #         method = getattr(self, "_" + name)
    #         ret = method()
    #         setattr(self, name, ret)
    #         return ret

    #     raise AttributeError(name)

    def codepoints(self):
        """
        Return a list of available character codes.
        """
        return list(self.keys())

    def charwidth(self, codepoint, font_size):
        return self.get(codepoint, self[32]).width * font_size / 1000.0

    def stringwidth(self, s, font_size, kerning=True, char_spacing=0.0):
        """
        Return the width of s when rendered in the current font in
        regular PostScript units. The boolean parameter kerning
        indicates whether the font’s pair-wise kerning information
        will be taken into account, if available. The char_spacing
        parameter is in regular PostScript units, too.
        """
        s = [ ord(c) for c in s ]

        if len(s) == 1:
            return self.charwidth(s[0], font_size)
        else:
            space_metric = self[32]
            width = sum([self.get(char, space_metric).width * font_size
                         for char in s])

            if kerning:
                for char, next in zip(s[:-1], s[1:]):
                    kerning = self.kerning_pairs.get(
                        (char, next,), 0.0 )
                    width += kerning * font_size

            if char_spacing > 0.0:
                width += (len(s) - 1) * char_spacing * 1000.0

            return width / 1000.0
