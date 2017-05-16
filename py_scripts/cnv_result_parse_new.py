import csv
import re
import sys
import os
import MySQLdb
import shutil
import codecs
from MySQLdb import cursors
import socket
import subprocess
import glob
import xml.etree.cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import get_Lit_from_redis as LIT

class Mention(object):
	def __init__(self, mention, start_offset, end_offset, sentence_id, pmid):
		self.mention = mention
		self.start_offset = start_offset
		self.end_offset = end_offset
		self.sentence_id = sentence_id
		self.pmid = pmid

	def show_myself(self):
		print self.mention
		print self.start_offset
		print self.end_offset
		print self.sentence_id
		print self.pmid


def connectDb(cnHost):
	db = MySQLdb.connect(host=cnHost, # your host, usually localhost
		 user='root', # your username
		  passwd='1234' , # your password
		  db='cnv_test',
		  #cursorclass = MySQLdb.cursors.SSCursor,
		  charset='utf8', 
		  use_unicode='True') # name of the database

	return db

def saveLit2db(db, literature):
	cur = db.cursor()

	save_sql = 'REPLACE INTO `cnv_test`.`literature` (`pmid`, `title`, `abstract`, `XML`, `year`, `journal`, `author`, `institution`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);'

	#print literature.pmid, ' being saved to db.'

	#Some weid year like 1994-1995
	literature.year = literature.year[:4]

	try:
		cur.execute(save_sql, (literature.pmid, literature.title, literature.abstract, literature.xml_str, literature.year, literature.journal, literature.author, literature.institution))
		db.commit()
	except:
		print(cur._last_executed)
		raise

	cur.close()


def isLegalCNV(s):
	p1 = "(\d\d?|[xyXY])[pqPQ]\d\d?([\-\~]?[pqPQ]?\d\d?)?(.\d\d?)*"
	p2 = "t\s?(\d\d?|x)"
	p3 = "[tT]risomy\s?(\d\d?|x)"
	p4 = "\s[xX][xX][xX]\s"
	p5 = "\s[xX][xX][yY]\s"

	if re.match(r'%s'%p1,s):
		return True

	if re.match(r'%s'%p2,s):
		return True

	if re.match(r'%s'%p3,s):
		return True	

	if re.match(r'%s'%p4,s):
		return True

	if re.match(r'%s'%p5,s):
		return True

	return False

def saveCNV2db(db, cnv_mention):
	cur = db.cursor()

	query_sql = 'select ifnull(max(cmid), 0)+1 from cnv_mention'
	cur.execute(query_sql)
	cmid = long(cur.fetchone()[0]) +  1

	if cnv_mention.mention.startswith('E'):
		cur.close()
		return

	save_sql = 'REPLACE INTO `cnv_test`.`cnv_mention` (`cmid`, `cnv_mention`, `sentence_id`, `start_offset`, `end_offset`, `literature_id`) VALUES (%s, %s, %s, %s, %s, %s);'

	#print literature.pmid, 'Literature saved to db.'
	try:
		cur.execute(save_sql, (long(cmid), cnv_mention.mention, long(cnv_mention.sentence_id), long(cnv_mention.start_offset), long(cnv_mention.end_offset), cnv_mention.pmid))
		db.commit()
	except:
		print(cur._last_executed)
		raise

	cur.close()

def saveDisease2db(db, disease_mention, disease2id)	:
	#disease_mention.show_myself()

	cur = db.cursor()
	query_sql = 'select ifnull(max(did), 0)+1 from disease_mention'
	cur.execute(query_sql)
	did = long(cur.fetchone()[0]) + 1

	save_sql = 'REPLACE INTO `cnv_test`.`disease_mention` (`did`, `disease_mention`, `sentence_id`, `start_offset`, `end_offset`, `disease_id`, `literature_id`) VALUES (%s, %s, %s, %s, %s, %s, %s);'

	#print 'Disease mention saved to db: ', disease_mention.mention

	try:
		mention = disease_mention.mention
		disease_id = mention
		if mention in disease2id.keys():
			disease_id = disease2id[mention]
		else:
			cur.close()
			return

		cur.execute(save_sql, (long(did), disease_mention.mention, long(disease_mention.sentence_id), long(disease_mention.start_offset), long(disease_mention.end_offset), disease_id, disease_mention.pmid))
		db.commit()
	except:
		print(cur._last_executed)
		raise

	cur.close()

def parse(db, xml_file, lits, disease2id):
	docElement = None
	pmids = set()

	parser = ET.XMLParser(encoding="utf-8")
	corpusRoot = ET.parse(xml_file, parser=parser)
	cnt = 0
	sentences = {}

	for document in corpusRoot.findall("document"):
		#Literature information parsing
		pmid = document.get("origId").strip()

		if pmid not in lits.keys():
			print pmid, 'not found!'
			continue

		literature = lits[pmid]
		cnt = cnt + 1

		if cnt % 100 ==0:
			print cnt, 'documents processed and saved to db.'

		saveLit2db(db, literature)

		#CNV information parsing
		doc_sentences = []

		for sentence in document.findall("sentence"):
			sentence_id = re.split(".s", sentence.get("id"))[1]
			sentence_text = sentence.get("text")
			doc_sentences.append((pmid, sentence_id, sentence_text))

			#There are cases where recognised disease entities overlap with CNV mentions, we prioritize CNV mentions. So we keep disease mentions in a list first.

			#lso = []
			#leo = []
			#ldm = []

			for entity in sentence.findall("entity"):
				etype = entity.get("type")
				offset = tuple(entity.get("charOffset").split('-'))
				mention = entity.get("text")
				#sentence_id = re.split(".s", sentence.get("id"))[1]

				mention_obj = Mention(mention, offset[0], offset[1], sentence_id, pmid)

				so = int(offset[0])
				eo = int(offset[1])

				if etype == "Disease":
					mention = mention.strip("+-:.,;~()[]/%'\">")
					mention_obj.mention = mention

					flag = 1

					if so > 0 and sentence_text[so-1].isalpha():
						flag = 0

					if eo < (len(sentence_text) - 1) and sentence_text[so-1].isalpha():
						flag = 0

					if len(mention) > 1 and flag >0 :
						saveDisease2db(db, mention_obj, disease2id)
						#ldm.append(mention_obj)
					continue

				if etype == "CNV":
					mention = mention.strip("+-:.,;~()[]/")
					mention_obj.mention = mention

					if len(mention) >1 and isLegalCNV(mention):
						saveCNV2db(db, mention_obj)
						#lso.append(so)
						#leo.append(eo)

			# for dm in ldm:
			# 	dso = dm.start_offset
			# 	deo = dm.end_offset

			# 	flag1 = 1

			# 	for i in range(0, len(lso)):
			# 		if dso >= lso[i] and dso < leo[i]:
			# 			flag1 = 0
			# 			break

			# 		if lso[i] >= dso and lso[i] < deo[i]:
			# 			flag1 = 0
			# 			break

			# 	if flag1:
			# 		saveDisease2db(db, dm, disease2id)

		sentences[pmid] = doc_sentences

	return sentences

def saveSentences2db(sentences):
	#REPLACE INTO `cnv_test`.`sentences`(`pmid`,`sid`,`stext`) VALUES(%s,%s,%s);
	dbHost = 'localhost'
	db = connectDb(dbHost)
	cur = db.cursor()

	print 'Saving the sentences information into db.'

	save_sql = 'REPLACE INTO `cnv_test`.`sentences`(`pmid`,`sid`,`stext`) VALUES(%s,%s,%s);'

	for pmid in sentences.keys():

		for sentence in sentences[pmid]:
			try:
				#pmid, sentence_id, sentence_text
				cur.execute(save_sql, (pmid, sentence[1], sentence[2]))
				db.commit()
			except:
				print(cur._last_executed)
				raise

	cur.close()
	db.commit()
	db.close()

def get_pmids(pmids_in):
	pmids = {}
	f = open(pmids_in, 'r')
	for pmid in f.readlines():
		pmid = pmid.strip()
		pmids[pmid] = 1
	f.close()
	return pmids	

def parseAll(db, xml_dir_path, disease2id, redis_server):
	#abspath = os.path.abspath(xml_dir_path)
	cnt = 0
	print 'Reading pmids from list file'
	pmids = get_pmids('cnv_pmids_2016161014.txt')	

	lits = LIT.getAllLitInfo(pmids, redis_server)

	all_sentences = {}

	for file in glob.glob(xml_dir_path + "/*.xml"):

		print 'Processing file:', file
		sentences = parse(db, file, lits, disease2id)
		saveSentences2db(sentences)
		all_sentences.update(sentences)
		
		cnt += 1
		print '%d xml document processed' % cnt

	return all_sentences

def gen3tables(disease2id, redis_server):
	dbHost = 'localhost'
	db = connectDb(dbHost)
	#parse(db, "cnv_sep_result/cnv7-preprocessed.xml")
	all_sentences = parseAll(db, "cnv_result",disease2id, redis_server)

	db.commit()
	db.close()

	return all_sentences

def getdisease2id(file):
	print 'Parsing disease and MESH mapping from cnv_disease_all.txt'
	disease2id = {}

	with open(file, 'r') as tsv:
		for line in csv.reader(tsv, delimiter="\t"): 
			if len(line) == 5 :
				disease2id[line[3]] = line[4]
			#else:
			#	disease2id[line[3]] = ''

	print 'Building the mapping from disease names to MESH/OMIM id.'

	return disease2id

def saveDiseaseId2db(disease2id, did2norm):
	dbHost = 'localhost'
	db = connectDb(dbHost)
	cur = db.cursor()

	print 'Saving the disease ID information into db.'

	save_sql = 'REPLACE INTO `cnv_test`.`disease` (`disease_name`,`disease_norm_id`, `disease_norm_name`, `data_source`) VALUES(%s, %s, %s, %s);'

	for disease in disease2id.keys():
		source = ''
		did = disease2id[disease]
		if did.startswith("MESH"):
			source = 'MESH'
		
		if did.startswith('OMIM'):
			source = 'OMIM'

		disease_norm_name = ""
		if did in did2norm.keys():
			disease_norm_name = did2norm[did]
		else:
			disease_norm_name = disease

		try:
			cur.execute(save_sql, (disease, did, disease_norm_name, source))
			db.commit()
		except:
			print(cur._last_executed)
			raise

	cur.close()
	db.commit()
	db.close()

def getLiteratureCNV():
	dbHost = 'localhost'
	db = connectDb(dbHost)
	cur = db.cursor()

	query_sql = 'SELECT pmid from literature;'

	try:
		cur.execute(query_sql)
		pmids = set()

		rows = cur.fetchall()

		for row in rows:
			pmids.add(row[0])

	except:
		print(cur._last_executed)
		raise

	cur.close()
	db.commit()
	db.close()

	print len(pmids), 'pmids found.'

	return pmids;

def cnvJoinDisease():
	cnv_disease = {}

	dbHost = 'localhost'
	db = connectDb(dbHost)
	cur = db.cursor()

	query_sql = "select cnv_mention.literature_id, cnv_mention.sentence_id, cnv_mention, cnv_mention.cmid, disease_mention, disease_mention.did, disease_mention.disease_id from cnv_mention, disease_mention where cnv_mention.literature_id = disease_mention.literature_id AND cnv_mention.sentence_id = disease_mention.sentence_id;"

	try:
		cur.execute(query_sql)
		rows = cur.fetchall()
		cnt = 0

		for row in rows:
			pmid = row[0]
			sid = row[1]
			cnv_mention = row[2]
			cmid = row[3]
			disease_mention = row[4]
			did = row[5]
			disease_id = row[6]

			evidence = (pmid, sid, cnv_mention, disease_mention, cmid, did, disease_id)

			if pmid in cnv_disease.keys():
				cnv_disease[pmid].append(evidence)
			else:
				cnv_disease[pmid] = [evidence]

			cnt = cnt + 1
			if cnt % 1000 == 0:
				print cnt, 'evidences processed.'
	except:
		print(cur._last_executed)
		raise

	cur.close()
	db.commit()
	db.close()

	print 'Disease and CNV correlation evidences found.'

	return cnv_disease

def evidence2db(cnv_disease):
	dbHost = 'localhost'
	db = connectDb(dbHost)
	cur = db.cursor()

	query_sql = 'select ifnull(max(id), 0)+1 from cnv_disease_rel'
	cur.execute(query_sql)
	eid = long(cur.fetchone()[0]) +  1

	ins_sql = 'REPLACE INTO `cnv_test`.`cnv_disease_rel`(`id`,`sentence_id`,`ddmid`,`cnv_mention_id`,`disease_mention_id`,`literature_id`, `cnv`, `disease_id`) VALUES(%s,%s,%s,%s,%s,%s,%s,%s);'

	cnt = 0

	for pmid in cnv_disease.keys():
		for evidence in cnv_disease[pmid]:
			try:
				cnt = cnt + 1
				#print 'Evidence for %s inserted. ' % pmid
				#Get ddmid first
				query_sql = 'select ddmid from cnv_test.dup_del_mention where literature_id = %s and sentence_id = %s'

				cur.execute(query_sql,(pmid, evidence[1]))

				result = cur.fetchone()
				ddmid = -1

				if result is not None:
					ddmid = result[0]

				cur.execute(ins_sql, (eid, evidence[1], ddmid, evidence[4], evidence[5], evidence[0], evidence[2], evidence[6]))
				eid = eid + 1
				#(pmid, sid, cnv_mention, disease_mention, cmid, did)
				if cnt % 100 ==0:
					print cnt, 'evidences processed.'

			except:
				print(cur._last_executed)
				raise

	cur.close()
	db.commit()
	db.close()

def getDupDel(sentences):
	dbHost = 'localhost'
	db = connectDb(dbHost)
	cur = db.cursor()

	query_sql = 'select ifnull(max(ddmid), 0)+1 from dup_del_mention'
	cur.execute(query_sql)
	ddmid = long(cur.fetchone()[0]) +  1	

	sql = 'REPLACE INTO `cnv_test`.`dup_del_mention`(`ddmid`,`dup_del_mention`,`polarity`,`sentence_id`,`start_offset`,`end_offset`,`literature_id`,`score`) VALUES(%s,%s,%s,%s,%s,%s,%s,%s);'

	regex = r"((dup)(lication)?s?)|((del)(etion)?s?)"
	pattern = re.compile(regex)

	for pmid in sentences.keys():
		#(pmid, sentence_id, sentence_text)
		for sentence in sentences[pmid]:
			sentence_id = sentence[1]
			sentence_text = sentence[2]

			result = pattern.finditer(sentence_text)

			for match in result:
				ddmid = ddmid + 1
				try:
					(so, eo) = match.span()
					ddmention = sentence_text[so:eo]

					if so > 0:
						if sentence_text[so-1].isalpha():
							ddmid = ddmid - 1
							continue

					if eo < len(sentence_text) - 1:
						if sentence_text[eo].isalpha():
							ddmid = ddmid - 1
							continue

					polarity = 'DUP'

					if ddmention.lower().startswith('del'):
						polarity = 'DEL'

					score = 1
					if len(ddmention) < 4 :
						score = 0.6

					cur.execute(sql, (ddmid, ddmention, polarity, sentence_id, so, eo, pmid, score))
				except:
					print(cur._last_executed)
					raise

	cur.close()
	db.commit()
	db.close()

def updateCnvDiseaseRel():
	dbHost = 'localhost'
	db = connectDb(dbHost)
	cur = db.cursor()


	cur.close()
	db.commit()
	db.close()

def diseaseId2Norm():
	parser = ET.XMLParser(encoding="utf-8")
	root = ET.parse("CTD_diseases.xml", parser=parser)
	id2norm = {}
	norm2id = {}
	id2cat = {}
	cat2disease = {}

	#Open C Diseases categories
	lines = [line.rstrip('\n') for line in open('C_Diseases.txt')]

	for line in lines:
		parts = line.split('-')
		k = parts[0].strip()
		v = parts[1].strip()
		cat2disease[k] = v
		#print (k,v)

	for row in root.findall('Row'):

		dne = row.find('DiseaseName')
		
		if dne is None:
			continue

		disease_name = dne.text 
		#print disease_name

		die = row.find('DiseaseID')

		if die is None:
			continue

		disease_id = die.text

		id2norm[disease_id] = disease_name

		if disease_name not in norm2id.keys():
			norm2id[disease_name] = disease_id
		else:
			norm2id[disease_name] = norm2id[disease_name]+'|'+disease_id

		#print "(%s, %s)" % (disease_id, disease_name)

		dtns = row.find('TreeNumbers').text.split('|')

		for dtn in dtns:
			dtn = dtn.replace("/", ".")
			if disease_id in id2cat.keys():
				id2cat[disease_id].add(dtn.split(".")[0])
			else:
				ts = set()
				ts.add(dtn.split(".")[0])
				id2cat[disease_id] = ts

		aies = row.find('AltDiseaseIDs')
		
		if aies is None:
			continue

		alt_disease_ids_str = aies.text
		
		for alt_id in alt_disease_ids_str.split('|'):
			id2norm[alt_id] = disease_name

			if disease_name not in norm2id.keys():
				norm2id[disease_name] = alt_id
			else:
				norm2id[disease_name] = norm2id[disease_name]+'|'+alt_id

	return (id2norm,id2cat,cat2disease,norm2id)

def getMentionedDiseaseIds():
	mentioned_disease_ids = set()

	dbHost = 'localhost'
	db = connectDb(dbHost)
	cur = db.cursor()

	query_sql = "select distinct(disease.disease_norm_id) from disease where disease.disease_norm_id in (select distinct(cnv_disease_rel.disease_id) from cnv_disease_rel);"

	try:
		cur.execute(query_sql)
		rows = cur.fetchall()

		for row in rows:
			mentioned_disease_ids.add(row[0])
	except:
		print(cur._last_executed)
		raise

	cur.close()
	db.commit()
	db.close()

	return mentioned_disease_ids

def getDiseaseCategories(mentioned_disease_ids, did2norm, id2cat, cat2disease):
	disease_categrories = [ ]

	for i in range(0, len(cat2disease.keys())):
		disease_categrories.append(set())

	for did in mentioned_disease_ids:
		if did not in id2cat.keys():
			continue

		cats = id2cat[did]

		#print did

		for cat in cats:
			if cat[0] != 'C':
				continue

			cat_no = int(cat[1:]) - 1
			#print cat_no

			norm_name = did2norm[did]
			disease_categrories[cat_no].add(norm_name)

	for cat in sorted(cat2disease.keys()):
		cat_no = int(cat[1:]) - 1
		#print "=====  C%d - %s ======" % (cat_no, cat2disease[cat])
		#print len(disease_categrories[cat_no])

		#for norm_name in disease_categrories[cat_no]:
		#	print norm_name

	return disease_categrories

if __name__ == "__main__":

	disease2id = getdisease2id('cnv_disease_all_161031.txt')
	(did2norm,id2cat, cat2disease,norm2id) = diseaseId2Norm()

	print len(disease2id), len(did2norm)
	

	#mentioned_disease_ids = getMentionedDiseaseIds()
	#getDiseaseCategories(mentioned_disease_ids, did2norm, id2cat, cat2disease)

	#print norm2id['IMMUNE SUPPRESSION']

	#saveDiseaseId2db(disease2id, did2norm)	
	#all_sentences = gen3tables(disease2id, sys.argv[1])
	#getDupDel(all_sentences)
	#pmids = getLiteratureCNV()
	#cnv_disease = cnvJoinDisease()
	#evidence2db(cnv_disease)
	




		

