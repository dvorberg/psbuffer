from io import BytesIO

from PIL import Image

from .measure import mm
from .dsc import Document, Page

document = Document()
page = document.append(Page())
canvas = page.append(Canvas(mm(18), mm(18), page.w-mm(36), page.h-mm(36)))


filepath = "/Users/diedrich/Desktop/Test.eps"
test_eps = open(filepath, "br")
img = EPSImage(test_eps, document_level=False, border=True,
               comment=filepath)
img.fit(canvas)

filename = "/Users/diedrich/Desktop/dings.png"
img = RasterImage(Image.open(filename),
                  border=True, comment=filename)
#img.fit(canvas)

fp = BytesIO()
document.write_to(fp)

print(fp.getvalue().decode("iso-8859-1"))
