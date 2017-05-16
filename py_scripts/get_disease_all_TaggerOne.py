import sys,os
import sys
import re
import glob
try:
        import xml.etree.cElementTree as ET
except ImportError:
        import cElementTree as ET
import codecs

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")

def get_TaggerOne_disease_from_xml(xml_file):
	tree = ET.ElementTree(file='%s' % xml_file)
	corpusRoot = tree.getroot()
	lines = []
	
	for docEle in corpusRoot.getiterator("document"):
		pmid = docEle.get('origId')

		for entity in docEle.getiterator('entity'):
			source = entity.get('source')

			if source == 'TaggerOne':
				charOffset = entity.get('charOffset')
				offsets = charOffset.split('-')
				start = offsets[0]
				end = offsets[1]
				mention = entity.get('text')
				normId = entity.get('normid')

				line = '%s\t%s\t%s\t%s\t%s\n' % (pmid, start, end, mention, normId)
				lines.append(line)
				#print line
	return lines

if __name__ == "__main__":
	f = codecs.open('cnv_disease_all_161031.txt', 'wt', 'utf-8')	
	for file in glob.glob( "cnv_result/*.xml"):
		print 'Processing file %s' % file
		lines = get_TaggerOne_disease_from_xml(file)

		for line in lines:
			f.write(line)

	f.close()




