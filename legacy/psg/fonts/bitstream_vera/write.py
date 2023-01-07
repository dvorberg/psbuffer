# Cool. This program writes itself!

import sys, re
from string import *

fullname_re = re.compile(r"/FontName /(.*) def", re.MULTILINE)

def fullname(pfb_filename):
    fp = open(pfb_filename)
    while True:
        for line in map(strip, fp.xreadlines()):
            match = fullname_re.match(line)
            if match is not None:
                return match.groups()[0]

    raise ValueError("No FullName entry in " + repr(pfb_filename))

for pfb_filename in sys.argv[1:]:
    long = fullname(pfb_filename).replace("BitstreamVera", "")
    identifyer = long.replace("-", "_").lower()
    print '%s = lazy_loader("%s") # %s' % (
        identifyer, pfb_filename.replace(".pfb", ""), long, )
    
