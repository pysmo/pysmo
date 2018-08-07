#!/usr/bin/env python

import os
from pysmo.sac import sacio

def open_sacfile():
    # Find the SAC testfile regardless of where we run the script from
    testfile = os.path.join(os.path.dirname(__file__), 'testfile.sac')
    return sacio.sacfile(testfile, 'ro')

def main():
    sacobj = open_sacfile()

if __name__ == "__main__":
    main()
