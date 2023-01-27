######################################################################
# When I grow up, I’ll be a unit test!

from io import BytesIO
from .base import PSBuffer

b = PSBuffer()

for a in ("white", "black", "red", "green", "blue"):
    b.print(globals().get(a), f"% {a}")

b.print()
b.print(WebColor("#FFBE33"), b'% WebColor("#FFBE33"))')

fp = BytesIO()
b.write_to(fp)

print(fp.getvalue().decode("ascii"))
