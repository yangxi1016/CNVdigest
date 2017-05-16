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
import unicode2ascii.unicode2ascii as U2A

def u2a_convert(id, in_str, tmp_suffix):
    if len(in_str) == 0:
        return ''

    ftmp_name = '/tmp/%s.%s' % (id, tmp_suffix)
    if isinstance(in_str, unicode):
        in_str = unicodedata.normalize('NFKD', in_str).encode('ascii', 'ignore')

    ftmp = open(ftmp_name, 'w')
    ftmp.write(in_str)
    ftmp.close()
    U2A.processFile(ftmp_name)
    ftmp_read = open(ftmp_name, 'r')
    new_str = ftmp_read.readlines()[0]
    new_str = re.sub(r'\s\s+', ' ', new_str)

    return new_str

def medline2txt(xml_in, pmids, job_size, output_dir):
        analyze_out = pp.parse_medline_xml(xml_in)
        bcnt = 0

        print 'Medline2Txt', xml_in

        for paper in analyze_out:
			pmid = paper['pmid']
			sub_dir = '%s/%d' % (output_dir,int(pmid) % job_size)

			if paper['pmid'] not in pmids:
					continue

			title = paper['title'].encode('utf-8').replace('\n', ' ')
			title = u2a_convert(pmid, title, 'title')

			abstract = ''
			if paper['abstract'] is not None:
				abstract = paper['abstract'].encode('utf-8').replace('\n', ' ')
				abstract = u2a_convert(pmid, abstract, 'abstract')
			else:
				print 'Cannot find abstract for PMID %s' % pmid

			f_tmp_in_fn = '%s/%s.txt' % (sub_dir,pmid)
			f_tmp_in = open(f_tmp_in_fn, 'w')
			#text = '%s|t|%s\n%s|a|%s\n' % (pmid, title, pmid, abstract) #PubTator Format
			text = '%s %s' % (title, abstract) # PWTEES FORMAT
			f_tmp_in.write(text)
			f_tmp_in.close()

			bcnt = bcnt + 1
			if bcnt % 1000 == 0 :
				print bcnt, 'medline records inserted.'

def medline2redis(xml_in, pmids, redis_server):
	analyze_out = pp.parse_medline_xml(xml_in)
	bcnt = 0

	r = redis.StrictRedis(host='%s' % redis_server, port=6379, db=0)
	pipe = r.pipeline()

	print 'Medline2Redis', xml_in
	
	for paper in analyze_out:

		pmid = paper['pmid']

		if paper['pmid'] not in pmids.keys():
			continue

		title = paper['title'].encode('utf-8').replace('\n', ' ')
		title = u2a_convert(pmid, title, 'title')

		abstract = ''
		if paper['abstract'] is not None:
			abstract = paper['abstract'].encode('utf-8').replace('\n', ' ')
			abstract = u2a_convert(pmid, abstract, 'abstract')
		else:
			print 'Cannot find abstract for PMID %s' % pmid

		#affiliation: corresponding author's affiliation
		#authors: authors, each separated by ;
		#mesh_terms: list of MeSH terms, each separated by ;
		#keywords: list of keywords, each separated by ;
		#pubdate: Publication date. Defaults to year information only.
		year = paper['pubdate']
		author = paper['author']
		keywords = paper['keywords']
		mesh_terms = paper['mesh_terms']
		affiliation = paper['affiliation']
		journal = paper['journal']

		pipe.set('%s:title' % pmid, '%s' % title)
		pipe.set('%s:abstract' % pmid, '%s' % abstract)
		pipe.set('%s:pubtator' % pmid, '%s|t|%s\n%s|a|%s' % (pmid, title, pmid, abstract))
		pipe.set('%s:pubdate' % pmid, year)
		pipe.set('%s:author' % pmid, author)
		pipe.set('%s:mesh_terms' % pmid, mesh_terms)
		pipe.set('%s:keywords' % pmid, keywords)
		pipe.set('%s:affiliation' % pmid, affiliation)
		pipe.set('%s:journal' % pmid, journal)

		bcnt = bcnt + 1
		if bcnt % 100 == 0 :
			print bcnt, 'cnv medline records inserted.'

	pipe.execute()

def get_pmids(pmids_in):
	print 'Getting PMIDs from %s' % pmids_in
	pmids = {}
	f = open(pmids_in, 'r')
	for pmid in f.readlines():
		pmid = pmid.strip()
		pmids[pmid] = 1
	f.close()
	return pmids	

if __name__ == "__main__":
	# === Get Options
	arg_parser = argparse.ArgumentParser()
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument("pmids", help="Specify the file containing PMIDs of interest.")
	arg_parser.add_argument("medline", help="Specify the file with MEDLINE baseline XML paths")
	arg_parser.add_argument("dest_dir", help="Specify the directory to store generated TXT files.")
	arg_parser.add_argument("-s", "--server", help="Specify the Redis server.")
	args = arg_parser.parse_args()
	pmid_fn = args.pmids
	medline_list_fn = args.medline
	dest_dir = args.dest_dir
	redis_server = args.server

	# =================================================
	# MPI initialization
	comm = MPI.COMM_WORLD
	rank = comm.Get_rank()
	size = comm.Get_size()
	name = MPI.Get_processor_name()

	if rank == 0:
		if not os.path.exists(dest_dir):
			os.makedirs(dest_dir)

		for i in range(0, size):
			sub_dir = '%s/%d' % (dest_dir, i)
			if not os.path.exists(sub_dir):
				os.makedirs(sub_dir)

	comm.Barrier()

	print 'Reading pmids and medline xml list'

	pmids = get_pmids(pmid_fn)
	medline_list_file = open(medline_list_fn, 'r')
	medline_list = medline_list_file.readlines()
	medline_list_file.close()
	print 'Done'

	for i in range(0, len(medline_list)):
		xml_in = medline_list[i].strip()
		print 'Processing medline xml %s' % xml_in

		if i % size == rank: 
			#print 'Processing %s on rank %d' % (xml_in, rank)
			if redis_server is not None:
				redis_server = sys.argv[1]
				medline2redis(xml_in, pmids, redis_server)
			else:

				medline2txt(xml_in, pmids, size, dest_dir)
