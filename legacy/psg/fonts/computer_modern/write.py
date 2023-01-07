# Cool. This program writes itself!

import re

fontmap = open("Fontmap.CMU").read()
entry_re = re.compile(r"/(.*?)\s+\((.*?)\.pfb\)\s*;")

result = entry_re.findall(fontmap)

result.sort(lambda a, b: cmp(a[0], b[0]))

for name, filename in result:
    long = name[3:].lower().replace("-", "_")
    short = filename

    print '%s = %s = lazy_loader("%s") # %s' % ( long, short, short, name, )
