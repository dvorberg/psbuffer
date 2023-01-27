from io import BytesIO

from psbuffer.dsc import EPSDocument, Page
from psbuffer.boxes import Canvas
from psbuffer.measure import mm
from psbuffer.utils import ps_escape

document = EPSDocument( (mm(100), mm(100),),
                        "The EPS page")
canvas = document.page.append(Canvas(mm(10), mm(10), mm(80), mm(80)))

canvas.print("/Helvetica findfont")
canvas.print("20 scalefont")
canvas.print("setfont")
canvas.print("0 0 moveto")
canvas.print(ps_escape("Hello, world!"), " show")

fp = BytesIO()
document.write_to(fp)

print(fp.getvalue().decode("iso-8859-1"))
