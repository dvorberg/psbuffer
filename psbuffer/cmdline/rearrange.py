import sys, os, os.path as op, string, re, datetime, argparse
import tempfile, shutil
from subprocess import run

from psbuffer.measure import parse_size
from psbuffer.dsc import Document, Page
from psbuffer.boxes import Canvas, EPSImage


filename_re = re.compile(br"page(\d+)\.eps")
page_re = re.compile(b"Page (\d+)")
def run_conversion(eps_to_document_f,
                   send_to_printer_f,
                   args):
    tmpdir = tempfile.mkdtemp()

    # Zerlegen der Eingabedatei in EPS dateien
    cmd = ["gs",
           "-sDEVICE=eps2write",
           "-sOutputFile=%s/page%%d.eps" % tmpdir,
           "-dNOPAUSE",
           "-dBATCH",
           args.infile_path, ]
    completed = run(cmd, capture_output=True)

    if completed.returncode != 0:
        raise IOError("Command execution failed: %s %s" % (
            " ".join(cmd), completed.stderr, ))

    # Check page lines. We don’t list the eps files in the output dir,
    # because Ghostscript sometimes creates an extra file *shrug*.
    result = page_re.findall(completed.stdout)
    pagenos = [ int(no) for no in result ]
    filenames = [ "page%i.eps" % pageno for pageno in pagenos ]

    # Let’s check if we have to pages available.
    #filenames = os.listdir(tmpdir)

    # Sort by pageno. listdir()’s order is arbitrary by definition.
    #def pageno(filename):
    #    match = filename_re.match(filename)
    #    return int(match.group(1))

    #filenames.sort(lambda a, b: cmp(pageno(a), pageno(b)))

    filepaths = [ op.join(tmpdir, filename) for filename in  filenames ]
    document = eps_to_document_f(filepaths)

    outps = op.join(tmpdir, "out.ps")
    outpdf = op.join(tmpdir, "out.pdf")

    with open(outps, "wb") as outfp:
        filename = outfp.name
        document.write_to(outfp)

    cmd = ["gs",
           "-sDEVICE=pdfwrite",
           "-sOutputFile=%s" % outpdf,
           "-dDEVICEWIDTHPOINTS=%i" % document.pages[0].w,
           "-dDEVICEHEIGHTPOINTS=%i" % document.pages[0].h,
           "-dNORANGEPAGESIZE",
           "-dAutoRotatePages=/None",
           "-dNOPAUSE",
           "-dBATCH",
           outps, ]
    completed = run(cmd, capture_output=True)

    if completed.returncode != 0:
        raise IOError("Command execution failed: %s %s" % (
            " ".join(cmd), completed.stderr, ))

    if args.output_path:
        shutil.copyfile(outpdf, args.output_path)
    else:
        send_to_printer_f(outpdf)

    if not args.debug:
        shutil.rmtree(tmpdir)



def booklet_main():
    """
    Rearange the pages of an A5 document into A4 sheets to form a booklet.
    """
    ap = argparse.ArgumentParser(description=booklet_main.__doc__)
    ap.add_argument("-o", dest="output_path",
                    help="Output pdf file. Do not send to printer.",
                    default=None)
    ap.add_argument("-c", dest="number_of_copies", help="Kopien",
                    default=1, type=int)
    ap.add_argument("-t", dest="printer_tray",
                    help="Einzugsfach des Druckers („Tray?“)",
                    default="Auto")
    ap.add_argument("-C", dest="color", action="store_true", default=False,
                    help="Use color printing mode on the printer, "
                    "otherwise output is monochrome.")
    ap.add_argument("-d", dest="debug", action="store_true", default=False,
                    help="If debugging is enabled, intermediate "
                    "files will be kept.")
    ap.add_argument("infile_path", metavar="infile", help="Input pdf file")

    args = ap.parse_args()

    def eps_to_document(filepaths):
        w, h = parse_size("a4 landscape")
        document = Document()

        # Create dummy entries at the end of filepaths
        # to fill up pages until their number is a multiple
        # of four.
        while len(filepaths) % 4 != 0:
            filepaths.append(None)

        args.input_pagecount = len(filepaths)

        def load_input_page(no):
            filepath = filepaths[no]
            if filepath is None:
                # Return a dummy object for an empty page.
                return Canvas(0, 0, w, h)
            else:
                return EPSImage(open(filepath, "rb"))

        inpagecount = len(filepaths)

        # Create the output pages.
        for counter in range(inpagecount // 2):
            outpage = document.append(Page( (w, h,) ))
            left = outpage # left side of the page
            # right side of the page
            right = outpage.append(Canvas(
                outpage.w / 2, 0, outpage.w/2, outpage.h))

            q = counter // 2

            if counter % 2 == 0:
                # Odd numbered output pages.
                left.append(load_input_page((inpagecount-1)-(q*2)))
                right.append(load_input_page(q*2))
            else:
                left.append(load_input_page(q*2+1))
                right.append(load_input_page((inpagecount)-(q*2+2)))

        return document

    def send_to_printer(outpdf_path):
        if args.color:
            CNColorMode="color"
            ColorModel="RGB"
            Resolution="600x600dpi"
        else:
            CNColorMode="mono"
            ColorModel="Gray"
            Resolution="1200x1200dpi"

        if args.input_pagecount == 4:
            num_copies = args.number_of_copies
            args.number_of_copies = 1
        else:
            num_copies = 1

        cmd = ("PRINTER=Canon "
               "lp "
               "-o InputSlot=%s "
               "-o collate=true "
               "-o media=a4 "
               "-o sides=two-sided-short-edge "
               "-o BindEdge=Top "
               "-o Resolution=%s "
               "-o CNColorMode=%s "
               "-o ColorModel=%s "
               "-n %i "
               "%s") % ( args.printer_tray,
                         Resolution, CNColorMode, ColorModel,
                         num_copies,
                         outpdf_path, )

        for n in range(args.number_of_copies):
            completed = run(cmd, capture_output=True)

            if completed.returncode != 0:
                raise IOError(completed.stderr)

    run_conversion(eps_to_document, send_to_printer, args)

    return 0


def leaflet_main():
    """
    Arrange a two page A5 document on one double sided A4 sheet for
    printing and cutting.
    """
    ap = argparse.ArgumentParser(description=leaflet_main.__doc__)
    ap.add_argument("-o", dest="output_path",
                    help="Output pdf file. Do not send to printer.",
                    default=None)
    ap.add_argument("-c", dest="number_of_copies", help="Kopien",
                    default=1, type=int)
    ap.add_argument("-t", dest="printer_tray",
                    help="Einzugsfach des Druckers („Tray?“)",
                    default="Tray1")
    ap.add_argument("-d", dest="debug", action="store_true", default=False,
                    help="If debugging is enabled, intermediate "
                    "files will be kept.")
    ap.add_argument("infile_path", metavar="infile", help="Input pdf file")

    args = ap.parse_args()

    def eps_to_document(filepaths):
        if len(filepaths) != 2:
            ap.error("Input file does not contain two pages.")

        w, h = parse_size("a4 landscape")
        document = Document()

        def make_page(eps_file_path):
            page = document.append(Page( (w, h,) ))
            inpage = EPSImage(open(eps_file_path, "br"),
                              document_level=True)

            # Left
            page.append(inpage)

            # Right
            right = page.append(Canvas(page.w / 2, 0, page.w/2, page.h))
            right.append(inpage)

        for path in filepaths:
            if os.stat(path).st_size == 0:
                args.error("Could not extract %s from %s" % (
                    fn, args.infile_path, ))

            make_page(path)

        return document

    def send_to_printer(outpdf_path):
        number_of_copies = args.number_of_copies / 2
        if number_of_copies < 1:
            number_of_copies = 1

        cmd = ("PRINTER=Canon lp -o InputSlot=%s "
               "-n %i -o collate=true "
               "-o media=a4 -o orientation-requested=4 "
               "-o sides=two-sided-short-edge "
               "-o BindEdge=Top "
               "-o Resolution=1200x1200dpi "
               "-o CNColorMode=mono "
               "-o ColorModel=Gray "
               "%s") % ( args.printer_tray, number_of_copies, outpdf_path, )
        completed = run(cmd, capture_output=True)

        if completed.returncode != 0:
            raise IOError(completed.stderr)

    run_conversion(eps_to_document, send_to_printer, args)

    return 0
