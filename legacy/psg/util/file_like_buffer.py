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
Buffers for output file generation 
"""

import sys, os
from string import *
from types import *
from cStringIO import StringIO

from t4.psg.exceptions import *
from misc import *

# Utilities for creating files

class file_like_buffer(list):
    """
    This class provides a minimal subset of a writable file: the
    write() and the writelines() method. It will store any string
    passed to these methods in an ordinary Python list. It provides
    two methods to acces its content (besides being the list of
    strings itself): as_string() returning the 'file's' content as an
    ordinary string and write_to() which will write the content to a
    file or file-like object using its write() method.

    No newslines will be added to any of the strings written.

    Instead of strings you may use any object providing a __str__ method
    """
    def __init__(self, *args):
        list.__init__(self, args)
        
        for a in self:
            if type(a) != StringType and not hasattr(a, "__str__"):
                raise TypeError("file_like_buffers can only 'contain' "
                                "string onjects or those reducable to "
                                "strings")
    
    def write(self, s):
        """
        Write string s to the buffer.
        """
        self.append(s)

    def writelines(self, l):
        """
        Writes a sequence of strings to the buffer. Uses the append
        operator to check if all of l's elements are strings.
        """
        for a in l: self.append(l)

    __add__ = writelines # Use append() because of type checking.

    def as_string(self):
        """
        Return the buffer as an ordinary string.
        """
        fp = StringIO()
        self.write_to(fp)
        return fp.getvalue()

    __str__ = as_string

    def write_to(self, fp):
        """
        Write the buffer to file pointer fp.
        """
        for a in self:
            if hasattr(a, "write_to"):
                a.write_to(fp)
            else:
                fp.write(str(a))
                
    def append(self, what):
        """
        Overwrite list's append() method to add type checking.
        """
        if what is None:
            return
        else:
            self.check(what)        
            list.append(self, what)

    def insert(self, idx, what):
        self.check(what)
        list.insert(self, idx, what)
            
    def prepend(self, what):
        """
        Insert an object as the first element of the list.
        """
        self.insert(0, what)

    def check(self, what):
        if type(what) != StringType and \
               not hasattr(what, "__str__") and \
               not hasattr(what, "write_to"):
            raise TypeError("You can only write strings to a "
                            "file_like_buffer, not %s" % repr(type(what))) 

    def _(self, *stuff):
        for a in stuff:
            print >> self, str(a)

            
        
class file_as_buffer:
    def __init__(self, fp):
        self.fp = fp
        self.filepointer = fp.tell()

    def write_to(self, fp):
        # Make sure the file pointer is at the desired position,
        # that is, the one, we were initialized with.
        self.fp.seek(self.filepointer)
        
        while True:
            s = self.fp.read(1024)
            if s == "":
                break
            else:
                fp.write(s)

    def as_string(self):
        return self.fp.read()
    
