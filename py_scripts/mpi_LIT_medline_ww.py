import glob
import os
import sys
import pubmed_parser as pp
import redis
from mpi4py import MPI
import shutil
import unicodedata
import re
import argparse

def medline2txt(xml_in, file):
        analyze_out = pp.parse_medline_xml(xml_in)
	bcnt = 0
        # print 'Medline2Txt', xml_in

        for paper in analyze_out:
			

		title = paper['title'].encode('utf-8').replace('\n', ' ')
		if isinstance(title, unicode):
			title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore')

		title = re.sub(r'\s\s+', ' ', title)

		abstract = paper['abstract'].encode('utf-8').replace('\n', ' ')
		if isinstance(abstract, unicode):
			abstract = unicodedata.normalize('NFKD', abstract).encode('ascii', 'ignore')

		abstract = re.sub(r'\s\s+', ' ', abstract)
		
		text = '%s %s\n' % (title, abstract) # PWTEES FORMAT
		file.write(text)

		bcnt = bcnt + 1
		if bcnt % 10000 == 0 :
			print bcnt, 'medline records inserted.'


if __name__ == "__main__":
	# =================================================
        # MPI initialization
        # comm = MPI.COMM_WORLD
        # rank = comm.Get_rank()
        # size = comm.Get_size()
        # name = MPI.Get_processor_name()

        medline_list_file = open('medline.list.2017', 'r')
        medline_list = medline_list_file.readlines()
        medline_list_file.close()

	txt = 'input_ww/pubmed_new.txt'
	file = open(txt,'wb')


        for i in range(0, len(medline_list)):
                xml_in = medline_list[i].strip()
                #print 'Processing medline xml %s' % xml_in

                # if i % size == rank:
                        #print 'Processing %s on rank %d' % (xml_in, rank)
                medline2txt(xml_in, file)

	file.close()
        print 'finish job!'

