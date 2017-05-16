import glob
import os
import sys
import pubmed_parser as pp
import redis
import unicode2ascii.unicode2ascii as U2A

def u2a_convert(pmid, in_str, tmp_suffix):
	if len(in_str) == 0:
		return '%s|a|' % pmid

	ftmp_name = '/tmp/%s.%s' % (pmid, tmp_suffix)
	ftmp = open(ftmp_name, 'w')
	ftmp.write(in_str)
	ftmp.close()
	U2A.processFile(ftmp_name)
	ftmp_read = open(ftmp_name, 'r')

	return ftmp_read.readlines()[0]

def medline2redis(xml_in, pmids, redis_server):
	analyze_out = pp.parse_medline_xml(xml_in)
	cnt=0
	bcnt = 0

	r = redis.StrictRedis(host='%s' % redis_server, port=6379, db=0)
	pipe = r.pipeline()

	print 'Medline2Redis', xml_in
	
	for paper in analyze_out:
		cnt = cnt + 1

		if cnt % 1000 == 0:
			print cnt, "medline records processed"

		pmid = paper['pmid']

		if paper['pmid'] not in pmids.keys():
			continue

		title = paper['title'].encode('utf-8').replace('\n', ' ')
		title = u2a_convert(pmid, title, "title")

		abstract = paper['abstract'].encode('utf-8').replace('\n', ' ')
		abstract = u2a_convert(pmid, abstract, "abstract")

		pipe.set('%s:title' % pmid, '%s' % title)
		pipe.set('%s:abstract' % pmid, '%s' % abstract)
		pipe.set('%s:pubtator' % pmid, '%s|t|%s\n%s|a|%s' % (pmid, title, pmid, abstract))

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
	if len(sys.argv) < 4:
		print 'Please specify job size, job id and redis server!'
		sys.exit()

	size = int(sys.argv[1])
	rank = int(sys.argv[2])
	redis_server = sys.argv[3]

	print 'Reading pmids and medline xml list'
	pmids = get_pmids('cnv_pmids_2016161014.txt')	
	medline_list_file = open('medline.list', 'r')
	medline_list = medline_list_file.readlines()
	medline_list_file.close()
	print 'Done'

	for i in range(0, len(medline_list)):
		xml_in = medline_list[i].strip()
		#print 'Processing medline xml %s' % xml_in

		if i % size == rank: 
			#print 'Processing %s on rank %d' % (xml_in, rank)
			medline2redis(xml_in, pmids, redis_server)

