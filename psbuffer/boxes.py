from base import PSBuffer, PSBufferWithSetup
from measure import Rectangle

class Box(PSBufferWithSetup, Rectangle):
    def __init__(self, x, y, w, h, border=False, clip=False, comment=""):
        PSBufferWithSetup.__init__(self)
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


    def _bonding_path(self):
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
    def __init__(self, x, y, w=0, h=0,
                 border=False, clip=False, comment=""):
        Box.__init__(self, x, y, w, h, border, clip, comment)

        # Move the origin to the lower left corner of the bounding box
        if x != 0 or y != 0:
            self.head.print(self.x, self.y, "translate")
