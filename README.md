CNVision：A webserver for systematic analysis of CNV-disease relationship

Genetic diseases are usually caused by chromosomal abnormalities, copy number variants (CNVs), or sequence mutations. Among them, pathogenic CNVs reportedly accounted for 3-20% diagnostic yield in different genetic disorders. The detection and interpretation of CNVs thus are of clinic importance in genetic testing. Several databases and web services are already being used by clinical geneticists to interpret the medical relevance of identified CNVs in patients. Often, geneticists or physicians would like to obtain the original literature context for more detailed information, especially with rare CNVs that were not included in databases.We met the demand by providing a user-friendly web interface for convenient queries to a database, in which all CNV/disease relationship documented in previous studies were dug out and structured with text mining techniques. The whole system was named CNVision（http://cnv.gtxlab.com）.


![image](https://github.com/yangxi1016/picture-cnvision/raw/master/1.png )

Three different query perspectives to users: 

 1) input a CNV to find the most relevant diseases as described in literature; 

![image](https://github.com/yangxi1016/picture-cnvision/raw/master/2.png )

 2) input a disease name or select one disease from a given list (indexed by disease MeSH terms) to find related CNVs;

![image](https://github.com/yangxi1016/picture-cnvision/raw/master/3.png )

 3) input a PubMed article ID (PMID) or a list of PMIDs to find CNV-diseases correlation in those articles.  

![image](https://github.com/yangxi1016/picture-cnvision/raw/master/4.png )

The results include a statistical summary and details of evidences from literature.
