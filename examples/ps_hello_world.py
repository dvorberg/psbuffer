from io import BytesIO

from psbuffer.dsc import Document, Page
from psbuffer.boxes import Canvas
from psbuffer.measure import mm
from psbuffer.utils import ps_escape

document = Document()
page = document.append(Page())
canvas = page.append(Canvas(mm(18), mm(18), page.w - mm(36), page.h - mm(36)))

canvas.print("/Helvetica findfont")
canvas.print("20 scalefont")
canvas.print("setfont")
canvas.print("0 0 moveto")
canvas.print(ps_escape("Hello, world!"), " show")

#fp = open("ps_hello_world.ps", "w")
#document.write_to(fp)
#fp.close()

fp = BytesIO()
document.write_to(fp)

print(fp.getvalue().decode("ascii"))

input()
