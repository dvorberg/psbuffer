######################################################################
# When I grow up, I’ll be a unit test!

from io import BytesIO

from psbuffer.base import PSBuffer
from psbuffer import colors

def main():
    b = PSBuffer()

    for a in ("white", "black", "red", "green", "blue"):
        b.print(getattr(colors, a), f"% {a}")

    b.print()
    b.print(colors.WebColor("#FFBE33"), b'% WebColor("#FFBE33"))')

    fp = BytesIO()
    b.write_to(fp)

    print(fp.getvalue().decode("ascii"))

main()
