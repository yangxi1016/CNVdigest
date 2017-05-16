import glob
import os
import sys
import pubmed_parser as pp
import redis
import unicode2ascii.unicode2ascii as U2A

def u2a_convert(pmcid, in_str, tmp_suffix):
	if len(in_str) == 0:
		return '%s|a|' % pmid

	ftmp_name = '/tmp/%s.%s' % (pmid, tmp_suffix)
	ftmp = open(ftmp_name, 'w')
	ftmp.write(in_str)
	ftmp.close()
	U2A.processFile(ftmp_name)
	ftmp_read = open(ftmp_name, 'r')

	return ftmp_read.readlines()[0]

def pmc2txt(xml_in, pmcid, job_size):
	pubmed_out = pp.parse_pubmed_xml(xml_in)
	ft_out = pp.parse_pubmed_paragraph(xml_in, all_paragraph=False)
	cnt=0
	bcnt = 0

	print 'PMC2Txt', xml_in

	pmcid_no = pmcid.replace('PMC', '')
	sub_dir = 'pmcinput/%d' % (int(pmcid_no) % job_size)

	full_text = ''

	for paragraph in ft_out:
		if 'text' in paragraph:
			full_text += paragraph['text']

	full_text = u2a_convert(pmcid, full_text, 'fulltext')

	if not os.path.exists(sub_dir):
		os.makedirs(sub_dir)

	f_tmp_in_fn = '%s/%s.txt' % (sub_dir,pmid)
	f_tmp_in = open(f_tmp_in_fn, 'w')

	#text = '%s|t|%s\n%s|a|%s\n' % (pmid, title, pmid, abstract) #PubTator Format
	#text = '%s %s' % (title, abstract) # PWTEES FORMAT
	f_tmp_in.write(full_text)
	f_tmp_in.close()


def pmc2redis(xml_in, pmcid, redis_server):
	pubmed_out = pp.parse_pubmed_xml(xml_in)
	ft_out = pp.parse_pubmed_paragraph(xml_in, all_paragraph=False)

	r = redis.StrictRedis(host='%s' % redis_server, port=6379, db=0)
	pipe = r.pipeline()

	print 'PMC2Redis', xml_in

	title = pubmed_out['title'].encode('utf-8').replace('\n', ' ')
	title = u2a_convert(pmcid, title, "title")

	abstract = pubmed_out['abstract'].encode('utf-8').replace('\n', ' ')
	abstract = u2a_convert(pmcid, abstract, "abstract")

	full_text = ''

	for paragraph in ft_out:
		if 'text' in paragraph:
			full_text += paragraph['text']

	full_text = u2a_convert(pmcid, full_text, 'fulltext')

	#affiliation: corresponding author's affiliation
	#authors: authors, each separated by ;
	#mesh_terms: list of MeSH terms, each separated by ;
	#keywords: list of keywords, each separated by ;
	#pubdate: Publication date. Defaults to year information only.
	year = pubmed_out['pubdate']
	author = pubmed_out['author']
	keywords = pubmed_out['keywords']
	mesh_terms = pubmed_out['mesh_terms']
	affiliation = pubmed_out['affiliation']
	journal = pubmed_out['journal']

	pipe.set('%s:title' % pmcid, '%s' % title)
	pipe.set('%s:abstract' % pmcid, '%s' % abstract)
	pipe.set('%s:fulltext' % pmcid, '%s' % full_text)
	pipe.set('%s:pubtator' % pmcid, '%s|t|%s\n%s|a|%s' % (pmcid, title, pmcid, abstract))
	pipe.set('%s:pubdate' % pmcid, year)
	pipe.set('%s:author' % pmcid, author)
	pipe.set('%s:mesh_terms' % pmcid, mesh_terms)
	pipe.set('%s:keywords' % pmcid, keywords)
	pipe.set('%s:affiliation' % pmcid, affiliation)
	pipe.set('%s:journal' % pmcid, journal)

	pipe.execute()

def get_pmids(pmids_in):
	pmids = {}
	f = open(pmids_in, 'r')
	for pmid in f.readlines():
		pmid = pmid.strip()
		pmids[pmid] = 1
	f.close()
	return pmids	

def get_ID_mappings(mapping_fn):
	mapping_file = open(mapping_fn, 'r')
	
	pmid2pmcid = {}
	pmcid2pmid = {}

	for line in mapping_file.readlines():
		line = line.strip()
		(pmcid, pmid) = line.split(',')
		pmcid = pmcid.strip()
		pmid = pmid.strip()
		pmid2pmcid[pmid] = pmcid
		pmcid2pmid[pmcid] = pmid
		#print '%s -> %s' % (pmid, pmcid)

	mapping_file.close()
	return (pmid2pmcid, pmcid2pmid)

def getpmcid2path(pmc_path_fn):
	pmcid2path = {}

	pmc_path_file = open(pmc_path_fn, 'r')

	for pmc_path in pmc_path_file.readlines():
		pmcid = os.path.basename(pmc_path).replace('.nxml', '')

		pmcid2path[pmcid] = pmc_path

	pmc_path_file.close()

	return pmcid2path

if __name__ == "__main__":
	if len(sys.argv) < 3:
		print 'Please specify job size, job id and redis server (optional)!'
		sys.exit()

	size = int(sys.argv[1])
	rank = int(sys.argv[2])

	print 'Reading pmids, pmc nxml list, and the mapping between PMIDs and PMCIDs'
	pmids = get_pmids('cnv_pmids20170221.txt')
	pmcid2path = getpmcid2path('/WORK/pp216/pmc_nxml_list_full.txt')
	print 'Done'

	(pmid2pmcid, pmcid2pmid) = get_ID_mappings('/WORK/pp216/pmc2017/PMC2PMID.txt')
	# print 'PMIDs:', pmid2pmcid.keys()

	valid_pmcids = []
	for pmid in pmids:
		if pmid not in pmid2pmcid.keys():
			continue

		valid_pmcids.append(pmid2pmcid[pmid])

	for i in range(0, len(valid_pmcids)):
		pmcid = valid_pmcids[i]

		if pmcid not in pmcid2path:
			continue

		xml_in = pmcid2path[pmcid].strip()
		print 'Processing PMC nxml %s' % xml_in

		if i % size == rank:
			#print 'Processing %s on rank %d' % (xml_in, rank)
			if len(sys.argv) == 4:
				redis_server = sys.argv[3]
				pmc2redis(xml_in, pmcid, redis_server)
			else:
				pmc2txt(xml_in, pmcid, size)