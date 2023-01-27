######################################################################
# When I grow up, I’ll be a unit test!

testfile_contents = b'''\
1234567890
abcdefghijklmnopqrstuvwxyz

Hello World!
I am a set of binary test data.
This is the end of the file -> .'''


# Let’s test this a little.

import os.path as op, tempfile


b = PSBuffer(b"1", "2", 3, 4.0)
b.write(5)
b.print(6, "7", b"8")

b.prepend(0)

outfp = io.BytesIO()
b.write_to(outfp)
assert outfp.getvalue() == b'01234.056 7 8\n', ValueError

######

with tempfile.TemporaryDirectory() as tmpdirpath:
    testfilepath = op.join(tmpdirpath, "test.txt")
    with open(testfilepath, "wb") as fp:
        fp.write(testfile_contents)


    with open(testfilepath, "br") as fp:
        sf = Subfile(fp, 11, 26)
        alphabet = sf.read()
        assert alphabet == b"abcdefghijklmnopqrstuvwxyz", ValueError

        ######

        fp.seek(0)
        bio = io.BytesIO(fp.read())
        sf = Subfile(bio, 11, 26)
        alphabet = sf.read()
        assert alphabet == b"abcdefghijklmnopqrstuvwxyz", ValueError
