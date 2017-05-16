import glob
import os
import sys
import pubmed_parser as pp
import redis
from mpi4py import MPI
import shutil
import unicodedata
import re
import argparse
import unicode2ascii.unicode2ascii as U2A

def u2a_convert(id, in_str, tmp_suffix):
    if len(in_str) == 0:
        return ''

    ftmp_name = '/tmp/%s.%s' % (id, tmp_suffix)
    if isinstance(in_str, unicode):
        in_str = unicodedata.normalize('NFKD', in_str).encode('ascii', 'ignore')

    ftmp = open(ftmp_name, 'w')
    ftmp.write(in_str)
    ftmp.close()
    U2A.processFile(ftmp_name)
    ftmp_read = open(ftmp_name, 'r')
    new_str = ftmp_read.readlines()[0]
    new_str = re.sub(r'\s\s+', ' ', new_str)

    return new_str

def pmc2txt(xml_in, pmcid, job_size, dest_dir):
    pubmed_out = pp.parse_pubmed_xml(xml_in)
    ft_out = pp.parse_pubmed_paragraph(xml_in, all_paragraph=False)
    cnt = 0
    bcnt = 0

    print 'PMC2Txt', xml_in

    pmcid_no = pmcid.replace('PMC', '')
    sub_dir = '%s/%d' % (dest_dir, int(pmcid_no) % job_size)

    full_text = ''

    for paragraph in ft_out:
        if 'text' in paragraph:
            full_text += paragraph['text']

    full_text = u2a_convert(pmcid, full_text, 'fulltext')

    if not os.path.exists(sub_dir):
        os.makedirs(sub_dir)

    f_tmp_in_fn = '%s/%s.txt' % (sub_dir, pmcid)
    f_tmp_in = open(f_tmp_in_fn, 'w')

    f_tmp_in.write(full_text)
    f_tmp_in.close()


def pmc2redis(xml_in, pmcid, redis_server):
    pubmed_out = pp.parse_pubmed_xml(xml_in)
    ft_out = pp.parse_pubmed_paragraph(xml_in, all_paragraph=False)

    r = redis.StrictRedis(host='%s' % redis_server, port=6379, db=0)
    pipe = r.pipeline()

    print 'PMC2Redis', xml_in

    title = pubmed_out['title'].encode('utf-8').replace('\n', ' ')
    title = u2a_convert(pmcid, title, 'title')

    abstract = ''
    if pubmed_out['abstract'] is not None:
        abstract = pubmed_out['abstract'].encode('utf-8').replace('\n', ' ')
        abstract = u2a_convert(pmcid, abstract, 'abstract')
    else:
        print 'Cannot find abstract for PMCID %s' % pmcid

    full_text = ''

    for paragraph in ft_out:
        if 'text' in paragraph:
            full_text += paragraph['text']

    full_text = u2a_convert(pmcid, full_text, 'fulltext')

    # affiliation: corresponding author's affiliation
    # authors: authors, each separated by ;
    # mesh_terms: list of MeSH terms, each separated by ;
    # keywords: list of keywords, each separated by ;
    # pubdate: Publication date. Defaults to year information only.
    year = pubmed_out['pubdate']
    author = pubmed_out['author']
    keywords = pubmed_out['keywords']
    mesh_terms = pubmed_out['mesh_terms']
    affiliation = pubmed_out['affiliation']
    journal = pubmed_out['journal']

    pipe.set('%s:title' % pmcid, '%s' % title)
    pipe.set('%s:abstract' % pmcid, '%s' % abstract)
    pipe.set('%s:fulltext' % pmcid, '%s' % full_text)
    pipe.set('%s:pubtator' % pmcid, '%s|t|%s\n%s|a|%s' % (pmcid, title, pmcid, abstract))
    pipe.set('%s:pubdate' % pmcid, year)
    pipe.set('%s:author' % pmcid, author)
    pipe.set('%s:mesh_terms' % pmcid, mesh_terms)
    pipe.set('%s:keywords' % pmcid, keywords)
    pipe.set('%s:affiliation' % pmcid, affiliation)
    pipe.set('%s:journal' % pmcid, journal)

    pipe.execute()


def get_pmids(pmids_in):
    pmids = {}
    f = open(pmids_in, 'r')
    for pmid in f.readlines():
        pmid = pmid.strip()
        pmids[pmid] = 1
    f.close()
    return pmids


def get_ID_mappings(mapping_fn, pmids):
    mapping_file = open(mapping_fn, 'r')

    pmid2pmcid = {}
    pmcid2pmid = {}

    #print 'Getting ID mappings'

    for line in mapping_file.readlines():
        line = line.strip()
        (pmcid, pmid) = line.split(',')
        pmcid = pmcid.strip()
        pmid = pmid.strip()

        if pmid in pmids:
            pmid2pmcid[pmid] = pmcid
            #print '%s -> %s' % (pmid, pmcid)

    mapping_file.close()
    return pmid2pmcid

def getpmcid2path(pmc_path_fn, pmcids):
    pmcid2path = {}

    pmc_path_file = open(pmc_path_fn, 'r')

    for pmc_path in pmc_path_file.readlines():
        pmc_path = pmc_path.strip()
        pmcid = os.path.basename(pmc_path).replace('.nxml', '')

        if pmcid in pmcids:
            pmcid2path[pmcid] = pmc_path

    pmc_path_file.close()

    return pmcid2path

if __name__ == "__main__":
    # === Get Options
    arg_parser = argparse.ArgumentParser()
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("pmids", help="Specify the file containing PMIDs of interest.")
    arg_parser.add_argument("idmap", help="Specify the mapping from PMID to PMCID")
    arg_parser.add_argument("pmc", help="Specify the file with PMC XML paths")
    arg_parser.add_argument("dest_dir", help="Specify the directory to store generated TXT files.")
    arg_parser.add_argument("-s", "--server", help="Specify the Redis server.")
    args = arg_parser.parse_args()
    cnv_pmids_fn = args.pmids
    id_mappings_fn = args.idmap
    pmc_nxml_list_fn = args.pmc
    dest_dir = args.dest_dir
    redis_server = args.server

    # =================================================
    # MPI initialization
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    name = MPI.Get_processor_name()

    if rank == 0:
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        for i in range(0, size):
            sub_dir = '%s/%d' % (dest_dir, i)
            if not os.path.exists(sub_dir):
                os.makedirs(sub_dir)

    comm.Barrier()

    #print 'Initializing relatede IDs and xml file paths on Rank %d' % rank

    #cnv_pmids_fn = 'cnv_pmids20170221.txt'
    #pmc_nxml_list_fn = '/WORK/pp216/pmc_nxml_list_full.txt'
    #id_mappings_fn = '/WORK/pp216/pmc2017/PMC2PMID.txt'

    pmids = get_pmids(cnv_pmids_fn)
    pmid2pmcid = get_ID_mappings(id_mappings_fn, pmids)
    pmcids = {key: 1 for key in pmid2pmcid.values()}
    pmcid2path = getpmcid2path(pmc_nxml_list_fn, pmcids)
    #print 'Initialization Done on Rank %d' % rank

    valid_pmcids = []

    cnt = 0
    for pmid in pmids.keys():

        if pmid not in pmid2pmcid:
            continue

        pmcid = pmid2pmcid[pmid]

        if pmcid not in pmcid2path:
            continue

        valid_pmcids.append(pmid2pmcid[pmid])

    print '%d PMIDs can be mapped to PMC IDs' % len(valid_pmcids)

    for i in range(0, len(valid_pmcids)):
        pmcid = valid_pmcids[i]
        xml_in = pmcid2path[pmcid].strip()

        if i % size == rank:
            print 'Processing %s on rank %d' % (xml_in, rank)
            if redis_server is not None:
                redis_server = sys.argv[1]
                pmc2redis(xml_in, pmcid, redis_server)
            else:
                pmc2txt(xml_in, pmcid, size, dest_dir)

    print 'Process %d finished successfully.' % rank

    sys.exit()