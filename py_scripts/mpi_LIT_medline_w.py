import glob
import os
import sys
import pubmed_parser as pp
import redis
from mpi4py import MPI
import shutil
import unicodedata

def medline2txt(xml_in, pmids, job_size):
        analyze_out = pp.parse_medline_xml(xml_in)
        bcnt = 0

        print 'Medline2Txt', xml_in

	sub_dir = 'input_w/'
	if not os.path.exists(sub_dir):
		os.makedirs(sub_dir)
        f_tmp_in_fn = '%s/medline.txt' % (sub_dir)
        f_tmp_in = open(f_tmp_in_fn, 'w')


        for paper in analyze_out:
		if paper['abstract'] is None:
			#print "abisnone: ",paper['pmid']
			continue
		abstract = paper['abstract'].encode('utf-8').replace('\n', ' ')
		if isinstance(abstract, unicode):
			abstract = unicodedata.normalize('NFKD', abstract).encode('ascii', 'ignore')

			
		#text = '%s|t|%s\n%s|a|%s\n' % (pmid, title, pmid, abstract) #PubTator Format
		text = '%s\n' % (abstract) # PWTEES FORMAT
		f_tmp_in.write(text)

		#bcnt = bcnt + 1
		#if bcnt % 1000 == 0 :
			#print bcnt, 'medline records inserted.'
	f_tmp_in.close()

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
		if isinstance(title, unicode):
			title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore')

		abstract = paper['abstract'].encode('utf-8').replace('\n', ' ')
		if isinstance(abstract, unicode):
			abstract = unicodedata.normalize('NFKD', abstract).encode('ascii', 'ignore')

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
	pmids = {}
	f = open(pmids_in, 'r')
	for pmid in f.readlines():
		pmid = pmid.strip()
		pmids[pmid] = 1
	f.close()
	return pmids	

if __name__ == "__main__":
	# =================================================
	# MPI initialization
	comm = MPI.COMM_WORLD
	rank = comm.Get_rank()
	size = comm.Get_size()
	name = MPI.Get_processor_name()

	print 'Reading pmids and medline xml list'
	pmids = get_pmids('beauty_pmids.txt')
	medline_list_file = open('medline.list.2017', 'r')
	medline_list = medline_list_file.readlines()
	medline_list_file.close()
	print 'Done'

	for i in range(0, len(medline_list)):
		xml_in = medline_list[i].strip()
		#print 'Processing medline xml %s' % xml_in

		if i % size == rank: 
			#print 'Processing %s on rank %d' % (xml_in, rank)
			medline2txt(xml_in, pmids, size)
        print 'finish job!'
