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

import os, os.path as op, re, struct, typing, pathlib, argparse
from collections.abc import Sequence

from .measure import Rectangle
from .base import encode, Subfile

# Lost In Single Paranthesis
#def car(l): return l[0]
#head = car
#def cdr(l): return l[1:]
#tail = cdr

#def toppop(l):
#    ret = l[0]
#    del l[0]
#    return ret

whitespace_re = re.compile(r"\s+")
def splitfields(s):
    return whitespace_re.split(s.strip())

class LineIterator(object):
    """
    Iterate over the lines in a file. Keep track of the line numbers.
    After a call to next() the file's seek indcator will point at the
    next byte after the newline. Lines are delimeted by either \r\n, \n,
    \r, which ever comes first, in this order. Lines that are longer
    than 10240 bytes will be returned as 10240 byte strings without a
    newline (because that's the buffer size).

    FIXME: This needs to be rewriten! Best in C, I guess.
    """
    def __init__(self, fp):
        """
        Make sure to open fp binary mode so no newline conversion is
        performed.
        """
        self.fp = fp
        self.line_number = 0
        self.last_line = None
        self.rolled_back = False

        if hasattr(fp, "encoding"):
            self.unix_newline = "\n"
            self.mac_newline = "\r"
        else:
            self.unix_newline = b"\n"
            self.mac_newline = b"\r"

    def __next__(self):
        if self.rolled_back:
            self.rolled_back = False
            return self.last_line

        old = self.fp.tell()
        buffer = self.fp.read(1024)

        bytes_read = len(buffer)
        if bytes_read == 0: # eof
            raise StopIteration
        else:
            unix_index = buffer.find(self.unix_newline)
            mac_index = buffer.find(self.mac_newline)

            if unix_index == -1 and mac_index == -1:
                self.last_line = buffer
                return buffer
            else:
                if unix_index == -1: unix_index = len(buffer)
                if mac_index == -1: mac_index = len(buffer)

            if unix_index == mac_index + 1:
                eol = mac_index + 1
            elif unix_index > mac_index:
                eol = mac_index
            else:
                eol = unix_index

            ret = buffer[:eol+1]

            self.fp.seek(old + len(ret), 0)

            self.line_number += 1
            self.last_line = ret

            return ret

    readline = __next__

    def rewind(self):
        """
        'Rewind' the file to the line before this one.

        @raises: IOError
        """
        if self.last_line is None or self.rolled_back:
            raise IOError("Cannot rollback LineIterator.")
        else:
            self.rolled_back = True
            return self.last_line

    def __iter__(self):
        return self


def copy_linewise(frm:typing.BinaryIO, to:typing.BinaryIO,
                  ignore_comments:bool=False):
    """
    This makes sure that all PostScript lines end with a regular
    Unix newline. (I'm not sure, what PostScript interpreters think of
    mixed-newline files.) Otherwise it does not alter the input stream
    and should be binary safe.
    """
    for line in line_iterator(frm):
        if not (ignore_comments and line.startswith(b"%%")):
            to.write(line.rstrip() + b"\n")



def join80(seq: Sequence[bytes]) -> bytes:
    r"""
    Like b" ".join(seq) except that it uses \n occasionly to
    create lines close to 80 characters in length.
    """
    if len(seq) == 0:
        return b""
    else:
        ret = bytearray(seq[0])
        length = len(seq[0])

        for a in seq[1:]:
            if length + len(a) > 80:
                ret.extend(b"\n")
                length = len(a)
            else:
                ret.extend(b" ")
                length += len(a) + 1

            ret.extend(a)

        return bytes(ret)

class PFBError(Exception): pass

def pfb2pfa(pfb:typing.BinaryIO, pfa:typing.BinaryIO):
    """
    Convert a PostScript Type1 font in binary representation (pfb) to
    ASCII representation (pfa). This function is modeled after the
    pfb2pfa program written in C by Piet Tutelaers. I freely admit
    that I understand only rudimentarily what I'm doing here.

    `pfa` and `pfb` must be file (-like) objects, opened for binary
    reading and writing, respectively.
    """

    def readone():
        bs = pfb.read(1)
        if bs == b"":
            return None
        else:
            return bs[0]

    while True:
        r = readone()
        if r != 128:
            raise PFBError("Not a pfb file! (%s)" % repr(r + pfb.read(50)))

        t = readone()

        if t == 1 or t == 2:
            l1 = readone()
            l2 = readone()
            l3 = readone()
            l4 = readone()

            l = l1 | l2 << 8 | l3 << 16 | l4 << 24

        if t == 1:
            for i in range(l):
                c = readone()
                if c == "\r":
                    pfa.write(b"\n")
                else:
                    pfa.write(bytes([c]))

        elif t == 2:
            for i in range(l):
                c = readone()
                pfa.write(b"%02x" % c)
                if (i + 1) % 30 == 0:
                    pfa.write(b"\n")

            pfa.write(b"\n")
        elif t == 3:
            break
        else:
            raise PFBError("Error in PFB file: unknown field type %i!" % t)


class pfb2pfa_Buffer(object):
    """
    A pfa2pfb buffer is a file like buffer which, initialized from a
    pfb file, will write a pfa file into its output file.
    """
    def __init__(self, pfb_fp:typing.BinaryIO):
        self.pfb = pfb_fp

    def write_to(self, fp):
        self.pfb.seek(0)
        pfb2pfa(self.pfb, fp)



hires_bbre = re.compile(
    br"%%HiResBoundingBox: (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) "
    br"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)")
bbre = re.compile(br"%%BoundingBox: (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) "
                  br"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)")
def get_eps_bb(fp_or_eps):
    """
    Provided EPS Source code, this function will return a pair of
    floats in PostScript units. If a %%HiResBoundingBox can’t be
    found, raise ValueError. The file pointer will be reset to the
    current position.
    """
    if hasattr(fp_or_eps, "read"):
        here = fp_or_eps.tell()
        eps = fp_or_eps.read(1024)
        fp_or_eps.seek(here)
    else:
        eps = remove_eps_preview(fp_or_eps[:1024])

    match = hires_bbre.search(eps)
    if match is None:
        match = bbre.search(eps)

    if match is not None:
        left, bottom, right, top = map(float, match.groups())
        return Rectangle(left, bottom, right, top)
    else:
        raise ValueError("Can’t find bounding box in EPS.")

def get_eps_size(fp_or_eps):
    bb = get_eps_bb(fp_or_eps)
    return (bb.w, bb.h)

def remove_eps_preview(epsdata):
    """
    Return the part of “epsdata” that contains the PostScript language
    code section.

    C.f. Encapsulated PostScript File Format Specification
         Adobe Developer Support, Version 3.0, 1 May 1992, pp. 24f.
    """
    if epsdata.startswith("%!PS-Adobe-"):
        return epsdata
    else:
        header = epsdata[:12]
        marker, pspos, pslength = struct.unpack("<III", header)
        # The manual says the marker must be c5d03d6d. That seems to be
        # little-endian or something. If I use this, plus “<” in unpack,
        # this works.
        if marker != 0xc6d3d0c5:
            raise IOError("Can’t identify image format.")
        return epsdata[pspos:pspos+pslength]

def eps_file_without_preview(epsfp):
    """
    Return a Subfile of epsfp, if it is an eps file that as a preview header.
    The file pointer will be reset to the current position.
    """
    here = epsfp.tell()
    header = epsfp.read(50)
    epsfp.seek(here)

    if header.startswith(b"%!PS-Adobe-"):
        # This EPS file does not have a header.
        return epsfp
    else:
        marker, pspos, pslength = struct.unpack("<III", header[:12])
        return Subfile(epsfp, pspos, pslength)

def pretty_wordlist(self_words):
    words = []
    for word in self_words:
        words.append(word)
        if word.space_width > 0:
            words.append(" ")

    if words:
        if words[-1] == " ":
            del words[-1]
        words[-1] = words[-1].with_hyphen()

        return "".join([str(w) for w in words])
    else:
        return ""


if __name__ == "__main__":
    print(join80(b"Lorem ipsum dolor sit amet, consetetur sadipscing elitr, "
                 b"sed diam nonumy eirmod tempor invidunt ut labore et dolore "
                 b"magna aliquyam erat, sed diam voluptua. At vero eos et "
                 b"accusam et justo duo dolores et ea rebum. Stet clita kasd "
                 b"gubergren, no sea takimata sanctus est Lorem ipsum dolor "
                 b"sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing "
                 b"elitr, sed diam nonumy eirmod tempor invidunt ut labore et "
                 b"dolore magna aliquyam erat, sed diam voluptua. At vero eos "
                 b"et accusam et justo duo dolores et ea rebum. Stet clita  "
                 b"gubergren, no sea takimata sanctus est Lorem ipsum dolor "
                 b"sit amet.".split(b" ")).decode("latin1"))
    print()

    import os.path as op
    from io import BytesIO

    outfp = BytesIO()
    with open(op.join(op.dirname(__file__),
                      "../legacy/examples/regular.pfb"), "rb") as infp:
              pfb2pfa(infp, outfp)

    print(outfp.getvalue().decode("latin1")[:400])
    print()
    print()

    with open(__file__, "rb") as fp:
        li = LineIterator(fp)
        for counter, line in enumerate(li):
            print(line.decode("utf-8").rstrip())

            if counter >= 4:
                break

        li.rewind()
        print(next(li).rstrip())

    print()
    print()

def default_filepath(filepath:str, ext:str):
    """
    Return a path derived from `filepath` with the file’s extension
    replaced by `ext`.
    """
    filepath = pathlib.Path(filepath)
    return filepath.parent.joinpath(filepath.stem + ext)

def make_example_argument_parser(
        main_file_path,
        description,
        i=False,      # Input .txt file
        o=True,       # Output .ps file
        s=False,      # Font size
        default_font_size=12,
        p=False,      # Paper size
        font=False):  # PFA und AFM file
    parser = argparse.ArgumentParser(description=description)

    txtfile = default_filepath(main_file_path, ".txt")
    psfile = default_filepath(main_file_path, ".ps")

    if i:
        parser.add_argument(
            "-i", "--input", default=txtfile,
            help=f"Input .txt file, defaults to {txtfile.name}.")

    if o:
        parser.add_argument(
            "-o", "--outfile", type=pathlib.Path, default=psfile,
            help=f"Output file, defaults to {psfile.name}.")

    if s:
        parser.add_argument(
            "-s", "--font-size", type=float, default=default_font_size,
            help="Font size in pt, defaults to 12.")

    if p:
        parser.add_argument(
            "-p", "--paper-size", dest="papersize", type=str, default="a4",
            help="Paper size known to psbuffer.measure.parse_size()."
            "Defaults to DIN A4.")

    if font:
        parser.add_argument(
            "-O", "--font-outline",
            help="PFA or PFB file. The font must contain polytonic "
            "Greek letters as composed glyphs for this to work. "
            "The provided Computer Modern Unicode Sans Serif "
            "works fine; it is also the default.",
            default=None,
            type=pathlib.Path)

        parser.add_argument("-M", "--font-metrics",
                            default=pathlib.Path(op.dirname(main_file_path),
                                                 "fonts",
                                                 "CMUSansSerif-Medium.afm"),
                            help="The corresponding AFM file.",
                            type=pathlib.Path)

    return parser

def make_font_instance_from_args(args):
    from psbuffer.fonts import Type1, ResidentType1

    # Load the font
    if args.font_outline is None:
        cmusr = ResidentType1(args.font_metrics.open())
    else:
        cmusr = Type1(args.font_outline.open(), args.font_metrics.open())

    instance = cmusr.make_instance(
        args.font_size, line_height=args.font_size*1.25)

    return instance
