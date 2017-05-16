import os
import subprocess
import redis
import sys
import re
from subprocess import Popen, PIPE

def tag_cnv(pmids_subset, redis_host, rank):
	for pmid in pmids_subset:
		r = redis.Redis(host='%s' % redis_host, port=6379, db=0)
		r3 = redis.Redis(host='%s' % redis_host, port=6379, db=3)

		tkey = '%s:title' % pmid
		tvalue = r.get(tkey)
		akey = '%s:abstract' % pmid
		avalue = r.get(akey)
			
		#Some pmid might not be in Redis (not in MEDLINE baseline)
		if tvalue is None:
			continue

		if avalue is None:
			avalue =''

		text ='%s %s' %(tvalue, avalue)

		pcnv0 = re.compile('(([1-9]\d?|[xyXY])[pqPQ][1-9]\d?([\-\~]?[pqPQ]?[1-9]\d?){0,}(\.[1-9]\d{0,1})*)')
		pcnv1 = re.compile('t\s?([1-9][0-9]?|x)')
		pcnv2 = re.compile('([tT]risomy\s?([1-9][0-9]?|x)*)')
		pcnv3 = re.compile('\s[xX][xX][xX]\s')
		pcnv4 = re.compile('\s[xX][xX][yY]\s')
		mcnt = 0

		pcnv_list = [pcnv0, pcnv1, pcnv2, pcnv3, pcnv4]

		pipe = r3.pipeline()

		for pcnv in pcnv_list:
			for m in re.finditer(pcnv, text):
				mresult = '%s\t%d\t%d\t%s' %(pmid, m.start(), m.end(), m.group(0))
				print mresult
				mkey = '%s:cnv:%d' % (pmid, mcnt)
				mcnt = mcnt + 1
				pipe.set(mkey, mresult)

		pipe.execute()

	print 'CNV tagging completed successfully'

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

	print 'Reading pmids'
	pmids = get_pmids('cnv_pmids_2016161014.txt').keys()

	pmids_subset = []
	for i in range(0, len(pmids)):
		if i % size == rank: 
			pmids_subset.append(pmids[i])

	print 'PMID subset size: %d' % len(pmids_subset)
	tag_cnv(pmids_subset, redis_server, rank)
