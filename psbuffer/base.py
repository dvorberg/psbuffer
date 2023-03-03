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
from collections.abc import Iterable

STRING_ENCODING="utf-8"

def encode(s):
    if type(s) is str:
        return s.encode(STRING_ENCODING)
    else:
        return s

def ps_escape(s, always_parenthesis:bool=True) -> bytes:
    """
    Return a PostScript string literal containing s.

    @param always_parenthesis: If set, the returned literal will always
      have ()s around it. If it is not set, this will only happen, if
      “s” contains a space char.

    This should probably be re-writen in C.
    """
    chars = encode(s)

    if not always_parenthesis and b" " in chars:
        always_parenthesis = True

    ret = bytearray()
    if always_parenthesis:
        ret.extend(b"(")

    for a in chars:
        if (a < 32) or (a in br"\()"):
            ret.extend(br"\03%o" % a)
        else:
            ret.append(a)

    if always_parenthesis:
        ret.extend(b")")

    return bytes(ret)


def ps_literal(value) -> bytes:
    """
    Convert Python primitive into a DSC literal. This will use
    Python's str() function on the value, because it produces ideal
    results for integer and float values. Strings will be quoted
    according to the DSC's rules as layed out in the specifications on
    page 36 (section 4.6, on <text>).
    """
    if type(value) in ( str, bytes, bytearray, ):
        return ps_escape(value, True)
    elif type(value) is float:
        ret = bytearray(b"%.3f" % value)
        while ret[-1] == b"0"[0]:
            del ret[-1]
        if ret[-1] == b"."[0]:
            del ret[-1]
        return ret
    elif isinstance(value, Iterable):
        return b"[ " + b" ".join([ps_literal(v) for v in value]) + b" ]"
    else:
        return encode(str(value))


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
        if type(thing) is bytes or \
           isinstance(thing, bytearray) \
           or hasattr(thing, "write_to"):
            return thing
        elif hasattr(thing, "__bytes__"):
            return bytes(thing)
        elif thing is None:
            return b""
        elif type(thing) is float:
            return ps_literal(thing)
        else:
            return bytes(str(thing).encode(STRING_ENCODING))

    def write(self, *things):
        self._things.extend([ self._convert(thing) for thing in things ])

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

    def clear(self):
        self._things = []

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
        if hasattr(self.fp, "write_to"):
            self.write_to = fp.write_to

    def write_to(self, fp):
        while True:
            r = self.fp.read(1024)
            if not r:
                break
            else:
                fp.write(r) # .replace(b"\r", b"\n")
