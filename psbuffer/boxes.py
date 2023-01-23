from uuid import uuid4 as uuid

from .base import PSBuffer
from .dsc import DSCBuffer, ResourceSection
from .measure import Rectangle
from .utils import eps_file_without_preview, get_eps_bb
from . import procsets

class BoxBuffer(DSCBuffer):
    def __init__(self):
        super().__init__()

        self.head = DSCBuffer()
        self.head.parent = self

        self.tail = DSCBuffer()
        self.tail.parent = self

    def write_to(self, fp):
        self.head.write_to(fp)
        super().write_to(fp)
        self.tail.write_to(fp)

    def push(self, for_head, for_tail=None):
        """
        Append for_head to head and prepent(!) for_tail to tail. If
        for_head and for_tail do not end in whitespace, push() will
        append a Unix newline to them before adding them to the
        buffer.
        """
        if for_head:
            for_head = self._convert(for_head)
            if for_head[-1] not in b"\n\t\r ":
                for_head += b"\n"

            self.head.write(for_head)

        if for_tail:
            for_tail = self._convert(for_tail)
            if for_tail[-1] not in b"\n\t\r ":
                for_tail = for_tail + b"\n"

            self.tail.prepend(for_tail)


class Box(BoxBuffer, Rectangle):
    def __init__(self, x, y, w, h, border=False, clip=False, comment=""):
        BoxBuffer.__init__(self)
        Rectangle.__init__(self, x, y, w, h)

        cmt = "%s: %s\n" % (self.__class__.__name__, comment)
        self.push("gsave % begin " + cmt,
                  "grestore % end " + cmt)

        if border:
            self.head.print(self._bounding_path())

            # Set color to black, line type to solid and width to 'hairline'
            self.head.print("0 setgray [] 0 setdash .1 setlinewidth")

            # Draw the line
            self.head.print("stroke")

        if clip:
            self.head.print(self._bounding_path())
            print >> self.head, "clip"


    def _bounding_path(self):
        ret = PSBuffer()
        print = ret.print

        # Set up a bounding box path
        print("newpath")
        print(self.x,          self.y,          "moveto")
        print(self.x,          self.y + self.h, "lineto")
        print(self.x + self.w, self.y + self.h, "lineto")
        print(self.x + self.w, self.y,          "lineto")
        print("closepath")

        return ret


class Canvas(Box):
    """
    A canvas is a bow to draw on. By now the only difference to a box
    is that it has its own coordinate system. PostScript's translate
    operator is used to relocate the canvas' origin to its lower left
    corner.
    """
    def __init__(self, x, y, w, h,
                 border=False, clip=False, comment=""):
        Box.__init__(self, x, y, w, h, border, clip, comment)

        # Move the origin to the lower left corner of the bounding box
        if x != 0 or y != 0:
            self.head.print(self.x, self.y, "translate")


class EPSBox(Box):
    """
    This is the base class for eps_image and raster_image below, which
    both embed external images into the target document as a Document
    section.
    """
    def __init__(self, subfile, bb, document_level, border, clip, comment):
        super().__init__(bb.llx, bb.lly, bb.w, bb.h, border, clip, comment)
        self.subfile = subfile
        self.document_level = document_level

    def on_parent_set(self):
        if self.document_level:
            # If the EPS file is supposed to live at document level,
            # we create a file resource in its prolog.

            # The mechanism was written and excellently explained by
            # Thomas D. Greer at http://www.tgreer.com/eps_vdp2.html .
            identifyer = "psg_eps_file*%i" % self.document.new_embed_number()
            resource = ResourceSection("file", str(uuid())+".eps")
            self.document.add_resource(resource)

            resource.print("/%sImageData currentfile" % identifyer)
            resource.print("<< /Filter /SubFileDecode")
            resource.print("   /DecodeParms << /EODCount")
            resource.print("       0 /EODString (***EOD***) >>")
            resource.print(">> /ReusableStreamDecode filter")
            resource.append(self.subfile)
            resource.print("***EOD***")
            resource.print("def")
            resource.print()
            resource.print("/%s " % identifyer)
            resource.print("<< /FormType 1")
            resource.print("   /BBox [%f %f %f %f]" % self.as_tuple())
            resource.print("   /Matrix [ 1 0 0 1 0 0]")
            resource.print("   /PaintProc")
            resource.print("   { pop")
            resource.print("       /ostate save def")
            resource.print("         /showpage {} def")
            resource.print("         /setpagedevice /pop load def")
            resource.print("         %sImageData 0 setfileposition"%identifyer)
            resource.print("            %sImageData cvx exec"%identifyer)
            resource.print("       ostate restore")
            resource.print("   } bind")
            resource.print(">> def")

            # Store the ps code to use the eps file in self
            self.print("%s execform" % identifyer)
        else:
            self.document.add_resource(procsets.embed_eps)
            self.print("psg_begin_epsf")
            self.print("%%BeginDocument")
            self.append(self.subfile)
            self.print()
            self.print("%%EndDocument")
            self.print("psg_end_epsf")

    def fit(self, canvas):
        """
        Fit this image into `canvas` so that it will set at (0,0) filling
        as much of the canvas as possible.  Return the size of the
        scaled image as a pair of floats (in PostScript units).
        """
        w = canvas.w
        factor = w / self.w
        h = self.h * factor

        if h > canvas.h:
            h = canvas.h
            factor = h / self.h
            w = self.w * factor

        canvas.print("gsave")
        canvas.print(factor, factor, "scale")
        canvas.append(self)
        canvas.print("grestore")

        return (w, h)

class EPSImage(EPSBox):
    """
    Include a EPS complient PostScript document into the target
    PostScript file.
    """
    def __init__(self, fp, document_level=False,
                 border=False, clip=False, comment=""):
        """
        @param fp: File pointer opened for reading of the EPS file to be
           included
        @param document_level: Boolean indicating whether the EPS file shall
           be part of the document prolog and be referenced several times from
           within the document, or if it shall be included where it is used
           for a single usage.
        """
        fp = eps_file_without_preview(fp)
        bb = get_eps_bb(fp)
        fp.seek(0)

        super().__init__(fp, bb, document_level, border, clip, comment)

class RasterImage(EPSBox):
    """
    This class creates a box from a raster image. Any image format
    supported by the Python Image Library is supported. The class uses
    PIL's EPS writer to create a PostScript representation of the
    image, which is much easier to program and much faster than
    anything I could have come up with, and uses PIL's output with the
    _eps_image class above. Of course, as any other part of psg, this
    is a lazy peration. When opening an image with it, PIL only reads
    the image header to determine its size and color depth. Conversion
    of the image takes place on writing.

    This assumes 72dpi raster images. Use _eps_image.fit() if needed.
    """
    class raster_image_buffer:
        def __init__(self, pil_image):
            self.pil_image = pil_image

        def write_to(self, fp):
            self.pil_image.save(fp, "EPS")

    def __init__(self, pil_image, document_level=False,
                 border=False, clip=False, comment=""):
        """
        @param pil_image: Instance of PIL's image class
        @param document_level: Boolean indicating whether the EPS file shall
           be part of the document prolog and be referenced several times from
           within the document or if it shall be included where it is used
           for a single usage.
        """
        width, height = pil_image.size
        bb = Rectangle(0, 0, width, height)

        if pil_image.mode != "CMYK":
            pil_image = pil_image.convert("CMYK")

        super().__init__(self.raster_image_buffer(pil_image),
                         bb, document_level, border, clip, comment)


if __name__ == "__main__":
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
