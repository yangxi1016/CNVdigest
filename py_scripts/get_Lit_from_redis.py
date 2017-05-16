import glob
import os
import sys
import redis


class Literature(object):
	#
	def __init__(self, pmid, title, abstract, xml_str, year, journal, author, institution):
		self.pmid = pmid
		self.title = title
		self.abstract = abstract
		self.xml_str = xml_str
		self.year = year
		self.journal = journal
		self.author = author
		self.institution = institution

	def show_myself(self):
		print "Literature Object Begins"
		print 'pmid', self.pmid
		print 'title', self.title
		print 'abstract', self.abstract
		print 'xml_str', self.xm_str
		print 'year', self.year
		print 'journal', self.journal
		print 'author', self.author
		print 'institution', self.institution
		print "Literature Object Ends"

def getAllLitInfo(pmids, redis_server):
	print 'Parsing MEDLINE citations from redis...'

	lits= {}
	cnt = 0
	r = redis.StrictRedis(host='%s' % redis_server, port=6379, db=0)

	for pmid in pmids:
		title = r.get('%s:title' % pmid)
		abstract = r.get('%s:abstract' % pmid)
		year = r.get('%s:year' % pmid)
		author = r.get('%s:author' % pmid)
		mesh_terms = r.get('%s:mesh_terms' % pmid)
		keywords = r.get('%s:keywords' % pmid)
		affiliation = r.get('%s:affiliation' % pmid)
		journal = r.get('%s:journal' % pmid)

		new_lit = Literature(pmid, title, abstract, '', year, journal, author, affiliation)

		lits[pmid] = new_lit
		cnt = cnt + 1

		if cnt % 1000 == 0:
			print cnt, ' MEDLINE records retrieved from redis.'

	return lits

def get_pmids(pmids_in):
	pmids = {}
	f = open(pmids_in, 'r')
	for pmid in f.readlines():
		pmid = pmid.strip()
		pmids[pmid] = 1
	f.close()
	return pmids	

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print 'Please specify redis server!'
		sys.exit()

	redis_server = sys.argv[1]

	print 'Reading pmids from list file'
	print 'Ready to obtain literature information from Redis' 
	pmids = get_pmids('cnv_pmids_2016161014.txt')	
	lits = getAllLitInfo(pmids, redis_server)
	print len(lits)
	for item in lits.items():
		print item
		break

	

	
