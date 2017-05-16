import os

outdir = "word2vec"
outfile = "%s/medline.txt" % outdir
o = open(outfile,"w")

rootdir = "input_w"
for parent,dirnames,filenames in os.walk(rootdir):

    for filename in filenames:
        f = open(os.path.join(parent, filename))
        for line in f.readlines():
            o.write("%s\n" % line)

o.close()
