import os
import subprocess
import redis
import sys
import re
from subprocess import Popen, PIPE

def call_tagger_one(pmids_subset, redis_host, rank):
	tagger_dir='/WORK/pp216/TaggerOne-0.2.1'
	cwd = os.getcwd()
	os.chdir(tagger_dir)
	node = os.uname()[1]
	tmp_in_fn = './temp/%s-%d.pubtator.txt' % (node, rank)
	tmp_out_fn = './temp/%s-%d.taggerone.out' % (node, rank)
	tmp_in = open(tmp_in_fn, 'w')

	#Get data from Redis
	r = redis.Redis(host='%s' % redis_host, port=6379, db=0)

	for pmid in pmids_subset:
		key = '%s:pubtator' % pmid
		value = r.get(key)
			
		#Some pmid might not be in Redis (not in MEDLINE baseline)
		if value is not None:
			#value = value.replace('| :', '|  ')
			value = re.sub('(?P<head>\d+\|[at]\|\s)\W', '\g<head> ', value)
			value = unicode(value.decode('utf-8'))
			tmp_in.write(value + '\n')

	tmp_in.close()
	print 'Pubtator input written.'

	#Calling TaggerOne to process
	print 'Calling TaggerOne....'

	process = Popen(['sh','%s/ProcessText.sh' % tagger_dir, '%s/output/model_NCBID.bin' % tagger_dir, tmp_in_fn, tmp_out_fn], stdin=PIPE, stdout=PIPE)

	stdout, stderr = process.communicate()

	if stderr != None:
		print >> sys.stderr, 'Error when calling TaggerOne'
		return

	print 'TaggerOne completed successfully'

	os.chdir(cwd)

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
	call_tagger_one(pmids_subset, redis_server, rank)
