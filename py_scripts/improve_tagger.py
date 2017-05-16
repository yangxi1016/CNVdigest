import os
import subprocess
import redis
import sys
import re
import glob
from subprocess import Popen, PIPE

def get_pmids(pmids_in):
	pmids = {}
	f = open(pmids_in, 'r')
	for pmid in f.readlines():
		pmid = pmid.strip()
		pmids[pmid] = 1
	f.close()
	return pmids

def ab3p_redis(pmids, redis_server):
	r0 = redis.Redis(host='%s' % redis_server, port=6379, db=0)
	r2 = redis.Redis(host='%s' % redis_server, port=6379, db=2)
	pipe = r2.pipeline()
	cnt = 0

	for pmid in pmids:
		keys = r0.keys('%s*' % pmid)

		if len(keys) == 0:
			continue

		os.chdir('../Ab3P-v1.5/')
		f_tmp_in_fn = '/tmp/%s.txt' % pmid
		f_tmp_in = open(f_tmp_in_fn, 'w')
		value = r0.get('%s:title' % pmid).replace('\n', ' ')
		f_tmp_in.write(value)
		f_tmp_in.write(' ')
		value = r0.get('%s:abstract' % pmid).replace('\n', ' ')
		f_tmp_in.write(value)
		f_tmp_in.close()

		cnt = cnt + 1

		if cnt % 100 == 0:
			print cnt, 'Ab3P processed. '

		process = Popen(['./identify_abbr', f_tmp_in_fn], stdin=PIPE, stdout=PIPE)

		stdout, stderr = process.communicate()

		if stderr != None:
			print >> sys.stderr, 'Error when calling Ab3p'
			print >> sys.stderr, 'PMID %s ' % pmid
			return
		else:
			#print stdout
			regex = re.compile("^\s+.+\|.+\|[\d\.]+$")
			cnt = 0
			for line in stdout.split('\n'):
				if re.match(regex, line) is not None:
					line = line.strip()
					pipe.set('%s:Ab3P:%d' % (pmid, cnt), line)
					cnt = cnt + 1

	pipe.execute()

def sflf_by_pmid(pmid, redis_server):
	sf2lf = {}
	lf2sf = {}

	r2 = redis.Redis(host='%s' % redis_server, port=6379, db=2)

	keys = r2.keys('%s:Ab3P:*' % pmid)

	for key in keys:
		values = r2.get(key).split('|')
		sf = values[0]
		lf = values[1]
		sf2lf[sf] = lf
		lf2sf[lf] = sf

	return sf2lf, lf2sf

def update_tagger_redis(pmids, redis_server):
	r = redis.Redis(host='%s' % redis_server, port=6379, db=1)
	pipe = r.pipeline()
	cnt = 0 
	cwd = os.getcwd()
	ab3p_redis(pmids, redis_server)

	for pmid in pmids.keys():
		os.chdir(cwd)

		keys = r.keys('%s:TaggerOne:*' % pmid)
		if len(keys) == 0:
			continue

		#if pmid != '3786199':
		#	continue

		disease2id = {}
		cnt = cnt + 1

		if cnt % 100 == 0:
			print cnt, 'pmids processed.'

		keys2do = []

		for key in keys:
			line = r.get(key)
			values = line.split('\t')

			if len(values) < 6:
				keys2do.append(key)
			else:
				disease2id[values[3]] = values[5]

		sf2lf, lf2sf = sflf_by_pmid(pmid, redis_server)

		for key in keys2do:
			line = r.get(key)
			values = line.split('\t')

			try:
				tmp_did = ''

				if values[3] in disease2id.keys():
					tmp_did = values[3]
				else:
					plf = values[3] + 's'
					if values[3] in sf2lf.keys():
						if sf2lf[values[3]] in disease2id.keys():
							tmp_did = sf2lf[values[3]]

					if plf in sf2lf.keys():
						if sf2lf[plf] in disease2id.keys():
							tmp_did = sf2lf[plf]

					if values[3] in lf2sf.keys():
						if lf2sf[values[3]] in disease2id.keys():
							tmp_did = lf2sf[values[3]]
					
					if tmp_did == '':
						print values[3], 'not found anyway'

				if tmp_did in disease2id.keys():
					newline = '%s\t%s\t%s\t%s\t%s\t%s' % (values[0], values[1], values[2], values[3], values[4], disease2id[tmp_did])
	
					pipe.set(key, newline)
			except:
				print 'ERROR', key, line

	pipe.execute()

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print >>sys.stderr, 'Please specify the redis server.'
		sys.exit()

	pmids = get_pmids('cnv_pmids_2016161014.txt')	

	update_tagger_redis(pmids, sys.argv[1])









