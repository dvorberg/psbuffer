#!/usr/bin/python

import sys, os
from string import *

import pexpect
from psg.util import line_iterator

def main(argv):
    fifo_name = argv[1]
    gs = pexpect.spawn("gs") # ["-dNOPAUSE"]

    gs.sendline("/__showpage__ {showpage} def /__showpage__ load")
    gs.sendline("/showpage {} def /showpage load")
    while True:

        fifo = open(fifo_name, "r")
        ps = fifo.read()
        fifo.close()
        
        gs.sendline("__showpage__")
        print ps
        gs.send(ps)
        gs.sendline("") # make sure the last command is execute by sending
                        # a newline in case the ps code doesn't end with one
        gs.read_nonblocking(10240, timeout=2)


main(sys.argv)
