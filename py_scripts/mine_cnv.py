import pubmed_parser as pp
import os
import sys
import glob

def get_Pubtator_from_medline_xml(xml_in, pmids, txt_out):
	analyze_out = pp.parse_medline_xml(xml_in)
	pubtator_out = open(txt_out, 'w')
	cnt=0
	
	for paper in analyze_out:
		cnt = cnt + 1
		if cnt % 1000 == 0:
			print cnt, "medline records processed"
		if paper['pmid'] not in pmids.keys():
			continue
		
		pubtator_out.write("%s|t|%s" % (paper['pmid'], paper['title'].encode('utf-8')))
		pubtator_out.write('\n')
		pubtator_out.write("%s|a|%s" % (paper['pmid'], paper['abstract'].encode('utf-8')))
		pubtator_out.write('\n')

	pubtator_out.close()

def get_file_basename(xml_in):
	base=os.path.basename(xml_in)
	
	return os.path.splitext(base)[0]

def get_pmids(pmids_in):
	pmids = {}
	f = open(pmids_in, 'r')

	for pmid in f.readlines():
		pmids[pmid] = 1

	f.close()
	return pmids	

if __name__ == "__main__":
	pmids = get_pmids('cnv_pmids_2016161014.txt')	
	#xml_in = "../data/medline16n0812.xml"
	print 'PMIDs imported'
	
	for xml_in in glob.glob("../data/*.xml"):
		print 'Processing %s' % xml_in
		get_Pubtator_from_medline_xml(xml_in, pmids, get_file_basename(xml_in)+'.txt')
 	
