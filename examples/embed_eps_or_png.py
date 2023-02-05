import argparse, pathlib
from io import BytesIO

from PIL import Image

from psbuffer.measure import mm
from psbuffer.dsc import Document, Page
from psbuffer.boxes import Canvas, EPSImage, RasterImage

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-s", "--papersize", default="a4")
    parser.add_argument("imgpath", type=pathlib.Path)

    args = parser.parse_args()

    document = Document()
    page = document.append(Page(size=args.papersize))
    canvas = page.append(Canvas(mm(18), mm(18), page.w-mm(36), page.h-mm(36)))

    if args.imgpath.suffix == ".eps":
        img = EPSImage(args.imgpath.open("rb"),
                       document_level=False, border=True,
                       comment=args.imgpath.name)
    else:
        img = RasterImage(Image.open(args.imgpath.open("rb")),
                          border=True, comment=args.imgpath.name)
    img.fit(canvas)

    fp = BytesIO()
    document.write_to(fp)

    print(fp.getvalue().decode("iso-8859-1"))


main()
