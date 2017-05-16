#!/usr/bin/env python

# Replaces Unicode characters in input text with ASCII
# approximations based on file with mappings between the two.

from __future__ import with_statement

import sys
import os
import codecs
import re
import shutil

verbose = True

# The name of the file from which to read the replacement. Each line
# should contain the hex code for the unicode character, TAB, and
# the replacement string.

MAPPING_FILE_NAME = "entities.dat"

# For statistics and summary of missing mappings in verbose mode
map_count = {}
missing_mapping = {}

def read_mapping(f, fn="mapping data"):
    """
    Reads in mapping from Unicode to ASCII from the given input stream
    and returns a dictionary keyed by Unicode characters with the
    corresponding ASCII characters as values. The expected mapping
    format defines a single mapping per line, each with the format
    CODE\tASC where CODE is the Unicode code point as a hex number and
    ASC is the replacement ASCII string ("\t" is the literal tab
    character). Any lines beginning with "#" are skipped as comments.
    """

    # read in the replacement data
    linere = re.compile(r'^([0-9A-Za-z]{4,})\t(.*)$')
    mapping = {}

    for i, l in enumerate(f):
        # ignore lines starting with "#" as comments
        if len(l) != 0 and l[0] == "#":
            continue

        m = linere.match(l)
        assert m, "Format error in %s line %s: '%s'" % (fn, i+1, l.replace("\n","").encode("utf-8"))
        c, r = m.groups()

        c = unichr(int(c, 16))
        assert c not in mapping or mapping[c] == r, "ERROR: conflicting mappings for %.4X: '%s' and '%s'" % (ord(c), mapping[c], r)

        # exception: literal '\n' maps to newline
        if r == '\\n':
            r = '\n'

        mapping[c] = r

    return mapping

def process(f, out, mapping):
    """
    Applies the given mapping to replace characters other than 7-bit
    ASCII from the given input stream f, writing the mapped text to
    the given output stream out.
    """
    global map_count, missing_mapping

    for c in f.read():
        if ord(c) >= 128:
            # higher than 7-bit ASCII, might wish to map
            if c in mapping:
                map_count[c] = map_count.get(c,0)+1
                c = mapping[c]
            else:
                missing_mapping[c] = missing_mapping.get(c,0)+1
                # escape into numeric Unicode codepoint
                c = "<%.4X>" % ord(c)
        out.write(c.encode("utf-8"))

def print_summary(out, mapping):
    """
    Prints human-readable summary of statistics and missing mappings
    for the input into the given output stream.
    """

    global map_count, missing_mapping

    print >> out, "Characters replaced       \t%d" % sum(map_count.values())    
    sk = map_count.keys()
    sk.sort(lambda a,b : cmp(map_count[b],map_count[a]))
    for c in sk:
        try:
            print >> out, "\t%.4X\t%s\t'%s'\t%d" % (ord(c), c.encode("utf-8"), mapping[c], map_count[c])
        except:
            print >> out, "\t%.4X\t'%s'\t%d" % (ord(c), mapping[c], map_count[c])
    print >> out, "Characters without mapping\t%d" % sum(missing_mapping.values())
    sk = missing_mapping.keys()
    sk.sort(lambda a,b : cmp(missing_mapping[b],missing_mapping[a]))
    for c in sk:
        try:
            print >> out, "\t%.4X\t%s\t%d" % (ord(c), c.encode("utf-8"), missing_mapping[c])
        except:
            print >> out, "\t%.4X\t?\t%d" % (ord(c), missing_mapping[c])

def processFile(fileList):
    #global options

    # argument processing
    input_file = fileList

    # read in mapping
    try:
        mapfn = MAPPING_FILE_NAME

        if not os.path.exists(mapfn):
            # fall back to trying in script dir
            mapfn = os.path.join(os.path.dirname(__file__), 
                                 os.path.basename(MAPPING_FILE_NAME))

        with codecs.open(mapfn, encoding="utf-8") as f:
            mapping = read_mapping(f, mapfn)
    except IOError, e:
        print >> sys.stderr, "Error reading mapping from %s: %s" % (MAPPING_FILE_NAME, e)
        return 1

    #print "Replacing Unicode\n"
    # primary processing
    fn = input_file

    if fn is not None:
    	try:
            if fn == '-':
                fn = '/dev/stdin' # TODO: make portable
            with codecs.open(fn, encoding="utf-8") as f:
                
                #bfn = os.path.basename(fn)
                ofn = os.path.splitext(fn)[0] + '.ascii'
                #print ofn
                with codecs.open(ofn, 'wt', encoding="utf-8") as out:
                        process(f, out, mapping)
			out.close()
		f.close()
		
		os.remove(fn)
		os.rename(ofn,fn) 
        except IOError, e:
            print >> sys.stderr, "Error processing %s: %s" % (fn, e)

    # optionally print summary of mappings
    #if options.verbose:
    #    print_summary(sys.stderr, mapping)

    return 0

if __name__ == "__main__":
    sys.exit(processFile(sys.argv[1:]))
