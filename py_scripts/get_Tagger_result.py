import os
import subprocess
import redis
import sys
import re
import glob

def tagger2redis(dir, redis_server):
	r = redis.Redis(host='%s' % redis_server, port=6379, db=1)

	regex1 = re.compile('(^\d+)\|[at]\|')
	regex2 = re.compile('(^\d+)\s')

	for file in glob.glob('%s/*.out' % dir):
		results = open(file, 'r')

		pmid = '' 

		c2flag = False
		cnt = 0
		for line in results.readlines():
			line = line.strip()
			check1 = re.match(regex1, line)
			check2 = re.match(regex2, line)

			if check1 is not None:
				pmid = check1.group(1)
				cnt = 0
	
			if check2 is not None:
				r.set('%s:%s:%d' % (pmid, 'TaggerOne', cnt), line)				
				cnt = cnt + 1
				
		print file, 'processed.'


if __name__ == "__main__":
	if len(sys.argv) < 3:
		print >>sys.stderr, 'Please specify the directory to be parsed and the redis server.'
		sys.exit()

	tagger2redis(sys.argv[1], sys.argv[2])









