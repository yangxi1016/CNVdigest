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
def medline2txt(xml_in, pmids, job_size):
        analyze_out = pp.parse_medline_xml(xml_in)
        cnt=0
        bcnt = 0

        print 'Medline2Txt', xml_in

        for paper in analyze_out:
                cnt = cnt + 1

                if cnt % 1000 == 0:
                        print cnt, "medline records processed"

                pmid = paper['pmid']
                sub_dir = 'input/%d' % (int(pmid) % job_size)

                if paper['pmid'] not in pmids.keys():
                        continue

                title = paper['title'].encode('utf-8').replace('\n', ' ')
                title = u2a_convert(pmid, title, "title")

                abstract = paper['abstract'].encode('utf-8').replace('\n', ' ')
                abstract = u2a_convert(pmid, abstract, "abstract")

                if not os.path.exists(sub_dir):
                        os.makedirs(sub_dir)
                f_tmp_in_fn = '%s/%s.txt' % (sub_dir,pmid)
                f_tmp_in = open(f_tmp_in_fn, 'w')
                #text = '%s|t|%s\n%s|a|%s\n' % (pmid, title, pmid, abstract) #PubTator Format
                text = '%s %s' % (title, abstract) # PWTEES FORMAT
		f_tmp_in.write(text)
                f_tmp_in.close()

                bcnt = bcnt + 1
                if bcnt % 100 == 0 :
                        print bcnt, 'cnv medline records inserted.'

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
	if len(sys.argv) < 3:
		print 'Please specify job size, job id and redis server (optional)!'
		sys.exit()

	size = int(sys.argv[1])
	rank = int(sys.argv[2])

	print 'Reading pmids and medline xml list'
	pmids = get_pmids('cnv_pmids20170221.txt')	
	medline_list_file = open('medline.list.2017', 'r')
	medline_list = medline_list_file.readlines()
	medline_list_file.close()
	print 'Done'

	for i in range(0, len(medline_list)):
		xml_in = medline_list[i].strip()
		print 'Processing medline xml %s' % xml_in

		if i % size == rank: 
			#print 'Processing %s on rank %d' % (xml_in, rank)
			if len(sys.argv) == 4:
				redis_server = sys.argv[3]
				medline2redis(xml_in, pmids, redis_server)
			else:
				medline2txt(xml_in, pmids, size)
