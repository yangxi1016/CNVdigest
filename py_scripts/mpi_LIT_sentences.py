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
import subprocess

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
    ftmp_read.close()

    return new_str

def get_sentences_by_geniass(pmid, in_str):
	f_tmp_in_fn = '/tmp/%s.txt' % pmid
	f_tmp_in = open(f_tmp_in_fn, 'w')
	f_tmp_in.write(in_str)
	f_tmp_in.close()
	f_tmp_out_fn = '/tmp/%s.sents' % pmid

	exitCode = subprocess.call("/WORK/pp216/geniass/run_geniass.sh %s %s" % (f_tmp_in_fn, f_tmp_out_fn), shell=True)

	if exitCode != 0:
		print 'Error in getting sentences from %s' % pmid

	f_sents = open(f_tmp_out_fn, 'r')
	sents = []
	scnt = 0 
	for line in f_sents.readlines():
		line = line.strip()
		sents.append('%s:%d\t%s' % (pmid, scnt, line))
		scnt += 1

	f_sents.close()
	return sents


def sents2txt(xml_in, output_file):
	analyze_out = pp.parse_medline_xml(xml_in)
	bcnt = 0

	print 'sents2txt ', xml_in

	sents = []

	for paper in analyze_out:
		pmid = paper['pmid']

		if paper['title'] is None:
			print '%s: title empty!' % pmid
			continue

		title = paper['title'].encode('utf-8').replace('\n', ' ')
		title = u2a_convert(pmid, title, 'title')

		abstract = ''
		if paper['abstract'] is not None:
			abstract = paper['abstract'].encode('utf-8').replace('\n', ' ')
			abstract = u2a_convert(pmid, abstract, 'abstract')
		else:
			print 'Cannot find abstract for PMID %s' % pmid

		txt_str = '%s %s' % (title, abstract)
		sub_sents = get_sentences_by_geniass(pmid, txt_str)
	
		sents += sub_sents

		if len(sents) > 1000:
			f_output = open(output_file, 'a')
			for sent in sents:
				f_output.write('%s\n' % sent)
			f_output.close()
			sents = []

		bcnt = bcnt + 1
		if bcnt % 100 == 0:
			print bcnt, 'medline records processed.'

	print 'Sentences written to file %s' % output_file

def sents2redis(xml_in, redis_server):
	analyze_out = pp.parse_medline_xml(xml_in)
	bcnt = 0

	r = redis.StrictRedis(host='%s' % redis_server, port=6379, db=0)
	pipe = r.pipeline()

	print 'Medline2Redis', xml_in
	
	for paper in analyze_out:
		pmid = paper['pmid']

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

		txt_str = '%s %s' % (title, abstract)
		sents = get_sentences_by_geniass(pmid, txt_str)
		scnt = 0
		for sent in sents:
			pipe.set('%s:sentence:%d' % (pmid, scnt), sent)
			scnt += 1

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
	arg_parser.add_argument("medline", help="Specify the file with MEDLINE baseline XML paths")
	arg_parser.add_argument("-s", "--server", help="Specify the Redis server.")
	args = arg_parser.parse_args()
	medline_list_fn = args.medline
	redis_server = args.server

	# =================================================
	# MPI initialization
	comm = MPI.COMM_WORLD
	rank = comm.Get_rank()
	size = comm.Get_size()
	name = MPI.Get_processor_name()

	print 'Reading medline xml list'

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
				sents2redis(xml_in, redis_server)
			else:
				sents2txt(xml_in, 'sents%d.tsv' % rank)


	comm.Barrier()
	print 'Job#%d done!' % rank
