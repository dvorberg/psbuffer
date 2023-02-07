#!/usr/bin/python

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
@var tables: Dict that maps PostScript encoding names to encoding
  tables. Encoding tables are dicts themselves mapping font char code to
  unicode char code.
"""
import os.path as op, re

glyph_name_to_codepoint = {}
codepoint_to_glyph_name = {}

#entry_re = re.compile(r"([A-Za-z0-9]+),([0-9a-f]+)")
with open(op.join(op.dirname(__file__), "glyph_name_to_unicode.csv")) as fp:
    for line_no, line in enumerate(fp.readlines()):
        line = line.rstrip()

        if not line or line[0] == "#":
            continue

        #match = entry_re.match(line)
        #if match is None:
        #    raise IOError(f"Illegal entry on line {line_no+1}: {repr(line)}")
        #else:
        #    glyph_name, codepoint = match.groups()
        #    codepoint = int(codepoint, 16)

        glyph_name, codepoint = line.split(",")
        codepoint = int(codepoint, 16)

        glyph_name_to_codepoint[glyph_name] = codepoint
        codepoint_to_glyph_name[codepoint] = glyph_name


adobe_standard_to_unicode = { 0x20:0x20,0x21:0x21,0x22:0x22,0x23:0x23,0x24:0x24,0x25:0x25,0x26:0x26,0x27:0x27,0x28:0x28,0x29:0x29,0x2a:0x2a,0x2b:0x2b,0x2c:0x2c,0x2d:0x2d,0x2e:0x2e,0x2f:0x2f,0x30:0x30,0x31:0x31,0x32:0x32,0x33:0x33,0x34:0x34,0x35:0x35,0x36:0x36,0x37:0x37,0x38:0x38,0x39:0x39,0x3a:0x3a,0x3b:0x3b,0x3c:0x3c,0x3d:0x3d,0x3e:0x3e,0x3f:0x3f,0x40:0x40,0x41:0x41,0x42:0x42,0x43:0x43,0x44:0x44,0x45:0x45,0x46:0x46,0x47:0x47,0x48:0x48,0x49:0x49,0x4a:0x4a,0x4b:0x4b,0x4c:0x4c,0x4d:0x4d,0x4e:0x4e,0x4f:0x4f,0x50:0x50,0x51:0x51,0x52:0x52,0x53:0x53,0x54:0x54,0x55:0x55,0x56:0x56,0x57:0x57,0x58:0x58,0x59:0x59,0x5a:0x5a,0x5b:0x5b,0x5c:0x5c,0x5d:0x5d,0x5e:0x5e,0x5f:0x5f,0x60:0x60,0x61:0x61,0x62:0x62,0x63:0x63,0x64:0x64,0x65:0x65,0x66:0x66,0x67:0x67,0x68:0x68,0x69:0x69,0x6a:0x6a,0x6b:0x6b,0x6c:0x6c,0x6d:0x6d,0x6e:0x6e,0x6f:0x6f,0x70:0x70,0x71:0x71,0x72:0x72,0x73:0x73,0x74:0x74,0x75:0x75,0x76:0x76,0x77:0x77,0x78:0x78,0x79:0x79,0x7a:0x7a,0x7b:0x7b,0x7c:0x7c,0x7d:0x7d,0x7e:0x7e,0x90:0x131,0x91:0x300,0x92:0x301,0x93:0x302,0x94:0x303,0x95:0x304,0x96:0x306,0x97:0x307,0x98:0x308,0x9a:0x30a,0x9b:0x327,0x9d:0x30b,0x9e:0x328,0x9f:0x30c,0xa0:0xa0,0xa1:0xa1,0xa2:0xa2,0xa3:0xa3,0xa4:0xa4,0xa5:0xa5,0xa6:0xa6,0xa7:0xa7,0xa8:0xa8,0xa9:0xa9,0xaa:0xaa,0xab:0xab,0xac:0xac,0xad:0xad,0xae:0xae,0xaf:0xaf,0xb0:0xb0,0xb1:0xb1,0xb2:0xb2,0xb3:0xb3,0xb4:0xb4,0xb5:0xb5,0xb6:0xb6,0xb7:0xb7,0xb8:0xb8,0xb9:0xb9,0xba:0xba,0xbb:0xbb,0xbc:0xbc,0xbd:0xbd,0xbe:0xbe,0xbf:0xbf,0xc0:0xc0,0xc1:0xc1,0xc2:0xc2,0xc3:0xc3,0xc4:0xc4,0xc5:0xc5,0xc6:0xc6,0xc7:0xc7,0xc8:0xc8,0xc9:0xc9,0xca:0xca,0xcb:0xcb,0xcc:0xcc,0xcd:0xcd,0xce:0xce,0xcf:0xcf,0xd0:0xd0,0xd1:0xd1,0xd2:0xd2,0xd3:0xd3,0xd4:0xd4,0xd5:0xd5,0xd6:0xd6,0xd7:0xd7,0xd8:0xd8,0xd9:0xd9,0xda:0xda,0xdb:0xdb,0xdc:0xdc,0xdd:0xdd,0xde:0xde,0xdf:0xdf,0xe0:0xe0,0xe1:0xe1,0xe2:0xe2,0xe3:0xe3,0xe4:0xe4,0xe5:0xe5,0xe6:0xe6,0xe7:0xe7,0xe8:0xe8,0xe9:0xe9,0xea:0xea,0xeb:0xeb,0xec:0xec,0xed:0xed,0xee:0xee,0xef:0xef,0xf0:0xf0,0xf1:0xf1,0xf2:0xf2,0xf3:0xf3,0xf4:0xf4,0xf5:0xf5,0xf6:0xf6,0xf7:0xf7,0xf8:0xf8,0xf9:0xf9,0xfa:0xfa,0xfb:0xfb,0xfc:0xfc,0xfd:0xfd,0xfe:0xfe,0xff:0xff }

adobe_symbol_to_unicode = { 0x20:0x20,0x21:0x21,0x22:0x22,0x23:0x23,0x24:0x24,0x25:0x25,0x26:0x26,0x27:0x27,0x28:0x28,0x29:0x29,0x2a:0x2a,0x2b:0x2b,0x2c:0x2c,0x2d:0x2d,0x2e:0x2e,0x2f:0x2f,0x30:0x30,0x31:0x31,0x32:0x32,0x33:0x33,0x34:0x34,0x35:0x35,0x36:0x36,0x37:0x37,0x38:0x38,0x39:0x39,0x3a:0x3a,0x3b:0x3b,0x3c:0x3c,0x3d:0x3d,0x3e:0x3e,0x3f:0x3f,0x40:0x40,0x41:0x41,0x42:0x42,0x43:0x43,0x44:0x44,0x45:0x45,0x46:0x46,0x47:0x47,0x48:0x48,0x49:0x49,0x4a:0x4a,0x4b:0x4b,0x4c:0x4c,0x4d:0x4d,0x4e:0x4e,0x4f:0x4f,0x50:0x50,0x51:0x51,0x52:0x52,0x53:0x53,0x54:0x54,0x55:0x55,0x56:0x56,0x57:0x57,0x58:0x58,0x59:0x59,0x5a:0x5a,0x5b:0x5b,0x5c:0x5c,0x5d:0x5d,0x5e:0x5e,0x5f:0x5f,0x60:0x60,0x61:0x61,0x62:0x62,0x63:0x63,0x64:0x64,0x65:0x65,0x66:0x66,0x67:0x67,0x68:0x68,0x69:0x69,0x6a:0x6a,0x6b:0x6b,0x6c:0x6c,0x6d:0x6d,0x6e:0x6e,0x6f:0x6f,0x70:0x70,0x71:0x71,0x72:0x72,0x73:0x73,0x74:0x74,0x75:0x75,0x76:0x76,0x77:0x77,0x78:0x78,0x79:0x79,0x7a:0x7a,0x7b:0x7b,0x7c:0x7c,0x7d:0x7d,0x7e:0x7e,0xa2:0x2032,0xa3:0x2264,0xa4:0x2215,0xa5:0x221e,0xa6:0x192,0xa7:0x2663,0xa8:0x2666,0xa9:0x2665,0xaa:0x2660,0xab:0x2194,0xac:0x2190,0xad:0x2191,0xae:0x2192,0xaf:0x2193,0xb0:0xb0,0xb1:0xb1,0xb2:0x2033,0xb3:0x2265,0xb4:0xd7,0xb5:0x221d,0xb6:0x2202,0xb7:0x2219,0xb8:0xf7,0xb9:0x2260,0xba:0x2261,0xbb:0x2248,0xbc:0x22ef,0xc6:0x2205,0xc7:0x2229,0xc8:0x222a,0xc9:0x2283,0xca:0x2287,0xcc:0x2282,0xcd:0x2286,0xce:0x2208,0xd0:0x2220,0xd1:0x2207,0xd5:0x220f,0xd6:0x221a,0xd7:0x22c5,0xd8:0xac,0xd9:0x2227,0xda:0x2228,0xdb:0x21d4,0xdc:0x21d0,0xdd:0x21d1,0xde:0x21d2,0xdf:0x21d3,0xe0:0x25ca,0xe1:0x2329,0xe5:0x2211,0xf1:0x232a,0xf2:0x222b }

apple_roman_to_unicode = { 0x20:0x20,0x21:0x21,0x22:0x22,0x23:0x23,0x24:0x24,0x25:0x25,0x26:0x26,0x27:0x27,0x28:0x28,0x29:0x29,0x2a:0x2a,0x2b:0x2b,0x2c:0x2c,0x2d:0x2d,0x2e:0x2e,0x2f:0x2f,0x30:0x30,0x31:0x31,0x32:0x32,0x33:0x33,0x34:0x34,0x35:0x35,0x36:0x36,0x37:0x37,0x38:0x38,0x39:0x39,0x3a:0x3a,0x3b:0x3b,0x3c:0x3c,0x3d:0x3d,0x3e:0x3e,0x3f:0x3f,0x40:0x40,0x41:0x41,0x42:0x42,0x43:0x43,0x44:0x44,0x45:0x45,0x46:0x46,0x47:0x47,0x48:0x48,0x49:0x49,0x4a:0x4a,0x4b:0x4b,0x4c:0x4c,0x4d:0x4d,0x4e:0x4e,0x4f:0x4f,0x50:0x50,0x51:0x51,0x52:0x52,0x53:0x53,0x54:0x54,0x55:0x55,0x56:0x56,0x57:0x57,0x58:0x58,0x59:0x59,0x5a:0x5a,0x5b:0x5b,0x5c:0x5c,0x5d:0x5d,0x5e:0x5e,0x5f:0x5f,0x60:0x60,0x61:0x61,0x62:0x62,0x63:0x63,0x64:0x64,0x65:0x65,0x66:0x66,0x67:0x67,0x68:0x68,0x69:0x69,0x6a:0x6a,0x6b:0x6b,0x6c:0x6c,0x6d:0x6d,0x6e:0x6e,0x6f:0x6f,0x70:0x70,0x71:0x71,0x72:0x72,0x73:0x73,0x74:0x74,0x75:0x75,0x76:0x76,0x77:0x77,0x78:0x78,0x79:0x79,0x7a:0x7a,0x7b:0x7b,0x7c:0x7c,0x7d:0x7d,0x7e:0x7e,0x80:0xc4,0x81:0xc5,0x82:0xc7,0x83:0xc9,0x84:0xd1,0x85:0xd6,0x86:0xdc,0x87:0xe1,0x88:0xe0,0x89:0xe2,0x8a:0xe4,0x8b:0xe3,0x8c:0xe5,0x8d:0xe7,0x8e:0xe9,0x8f:0xe8,0x90:0xea,0x91:0xeb,0x92:0xed,0x93:0xec,0x94:0xee,0x95:0xef,0x96:0xf1,0x97:0xf3,0x98:0xf2,0x99:0xf4,0x9a:0xf6,0x9b:0xf5,0x9c:0xfa,0x9d:0xf9,0x9e:0xfb,0x9f:0xfc,0xa0:0x2020,0xa1:0xb0,0xa2:0xa2,0xa3:0xa3,0xa4:0xa7,0xa5:0x2219,0xa6:0xb6,0xa7:0xdf,0xa8:0xae,0xa9:0xa9,0xaa:0x2122,0xab:0xb4,0xac:0xa8,0xad:0x2260,0xae:0xc6,0xaf:0xd8,0xb0:0x221e,0xb1:0xb1,0xb2:0x2264,0xb3:0x2265,0xb4:0xa5,0xb5:0xb5,0xb6:0x2202,0xb7:0x2211,0xb8:0x220f,0xb9:0x3c0,0xba:0x222b,0xbb:0xaa,0xbc:0xba,0xbd:0x3a9,0xbe:0xe6,0xbf:0xf8,0xc0:0xbf,0xc1:0xa1,0xc2:0xac,0xc3:0x221a,0xc4:0x192,0xc5:0x2248,0xc6:0x394,0xc7:0xab,0xc8:0xbb,0xc9:0x22ef,0xca:0xa0,0xcb:0xc0,0xcc:0xc3,0xcd:0xd5,0xce:0x152,0xcf:0x153,0xd0:0x2013,0xd1:0x2014,0xd2:0x201c,0xd3:0x201d,0xd4:0x2018,0xd5:0x2019,0xd6:0xf7,0xd7:0x25ca,0xd8:0xff,0xd9:0x178,0xda:0x2044,0xdb:0xa4,0xdc:0x2039,0xdd:0x203a,0xde:0xfb01,0xdf:0xfb02,0xe0:0x2021,0xe1:0xb7,0xe2:0x201a,0xe3:0x201e,0xe4:0x2030,0xe5:0xc2,0xe6:0xca,0xe7:0xc1,0xe8:0xcb,0xe9:0xc8,0xea:0xcd,0xeb:0xce,0xec:0xcf,0xed:0xcc,0xee:0xd3,0xef:0xd4,0xf1:0xd2,0xf2:0xda,0xf3:0xdb,0xf4:0xd9,0xf5:0x131,0xf6:0x302,0xf7:0x303,0xf8:0xaf,0xf9:0x2d8,0xfa:0x2d9,0xfb:0x2da,0xfc:0xb8,0xfd:0x2dd,0xfe:0x2db,0xff:0x2c7 }

iso_latin1_to_unicode = { 0x20:0x20,0x21:0x21,0x22:0x22,0x23:0x23,0x24:0x24,0x25:0x25,0x26:0x26,0x27:0x27,0x28:0x28,0x29:0x29,0x2a:0x2a,0x2b:0x2b,0x2c:0x2c,0x2d:0x2d,0x2e:0x2e,0x2f:0x2f,0x30:0x30,0x31:0x31,0x32:0x32,0x33:0x33,0x34:0x34,0x35:0x35,0x36:0x36,0x37:0x37,0x38:0x38,0x39:0x39,0x3a:0x3a,0x3b:0x3b,0x3c:0x3c,0x3d:0x3d,0x3e:0x3e,0x3f:0x3f,0x40:0x40,0x41:0x41,0x42:0x42,0x43:0x43,0x44:0x44,0x45:0x45,0x46:0x46,0x47:0x47,0x48:0x48,0x49:0x49,0x4a:0x4a,0x4b:0x4b,0x4c:0x4c,0x4d:0x4d,0x4e:0x4e,0x4f:0x4f,0x50:0x50,0x51:0x51,0x52:0x52,0x53:0x53,0x54:0x54,0x55:0x55,0x56:0x56,0x57:0x57,0x58:0x58,0x59:0x59,0x5a:0x5a,0x5b:0x5b,0x5c:0x5c,0x5d:0x5d,0x5e:0x5e,0x5f:0x5f,0x60:0x60,0x61:0x61,0x62:0x62,0x63:0x63,0x64:0x64,0x65:0x65,0x66:0x66,0x67:0x67,0x68:0x68,0x69:0x69,0x6a:0x6a,0x6b:0x6b,0x6c:0x6c,0x6d:0x6d,0x6e:0x6e,0x6f:0x6f,0x70:0x70,0x71:0x71,0x72:0x72,0x73:0x73,0x74:0x74,0x75:0x75,0x76:0x76,0x77:0x77,0x78:0x78,0x79:0x79,0x7a:0x7a,0x7b:0x7b,0x7c:0x7c,0x7d:0x7d,0x7e:0x7e,0x90:0x131,0x91:0x300,0x92:0x301,0x93:0x302,0x94:0x303,0x95:0x304,0x96:0x306,0x97:0x307,0x98:0x308,0x9a:0x30a,0x9b:0x327,0x9d:0x30b,0x9e:0x328,0x9f:0x30c,0xa0:0xa0,0xa1:0xa1,0xa2:0xa2,0xa3:0xa3,0xa4:0xa4,0xa5:0xa5,0xa6:0xa6,0xa7:0xa7,0xa8:0xa8,0xa9:0xa9,0xaa:0xaa,0xab:0xab,0xac:0xac,0xad:0xad,0xae:0xae,0xaf:0xaf,0xb0:0xb0,0xb1:0xb1,0xb2:0xb2,0xb3:0xb3,0xb4:0xb4,0xb5:0xb5,0xb6:0xb6,0xb7:0xb7,0xb8:0xb8,0xb9:0xb9,0xba:0xba,0xbb:0xbb,0xbc:0xbc,0xbd:0xbd,0xbe:0xbe,0xbf:0xbf,0xc0:0xc0,0xc1:0xc1,0xc2:0xc2,0xc3:0xc3,0xc4:0xc4,0xc5:0xc5,0xc6:0xc6,0xc7:0xc7,0xc8:0xc8,0xc9:0xc9,0xca:0xca,0xcb:0xcb,0xcc:0xcc,0xcd:0xcd,0xce:0xce,0xcf:0xcf,0xd0:0xd0,0xd1:0xd1,0xd2:0xd2,0xd3:0xd3,0xd4:0xd4,0xd5:0xd5,0xd6:0xd6,0xd7:0xd7,0xd8:0xd8,0xd9:0xd9,0xda:0xda,0xdb:0xdb,0xdc:0xdc,0xdd:0xdd,0xde:0xde,0xdf:0xdf,0xe0:0xe0,0xe1:0xe1,0xe2:0xe2,0xe3:0xe3,0xe4:0xe4,0xe5:0xe5,0xe6:0xe6,0xe7:0xe7,0xe8:0xe8,0xe9:0xe9,0xea:0xea,0xeb:0xeb,0xec:0xec,0xed:0xed,0xee:0xee,0xef:0xef,0xf0:0xf0,0xf1:0xf1,0xf2:0xf2,0xf3:0xf3,0xf4:0xf4,0xf5:0xf5,0xf6:0xf6,0xf7:0xf7,0xf8:0xf8,0xf9:0xf9,0xfa:0xfa,0xfb:0xfb,0xfc:0xfc,0xfd:0xfd,0xfe:0xfe,0xff:0xff }

encoding_tables = { "AppleStandard": apple_roman_to_unicode,
                    "AdobeStandardEncoding": adobe_standard_to_unicode,
                    "ISOLatin1Encoding": iso_latin1_to_unicode,
                    "Symbol": adobe_symbol_to_unicode }
