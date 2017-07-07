#enrichrAPI.py
#Russell Stewart
#7/6/2017
#Allows a user to specify a .txt file of genes, an output file, and a list of
#gene sets to batch analyze in Enrichr, eliminating the need for using UIs with
#the website.
#
#PROGRAM OPTIONS:
#python enrichrAPI.py --ifile <iFilePath> --ofile <oFilePath> --libraries <libraryFilePath> [--minOverlap] <int>]
#--ifile: the file path for the input (.txt) file. should have two columns: first has gene names, second has corresponding modules
#--ofile: the file path for the output (.xlsx) file with the Enrichr results
#--libraries: the Enrichr-compatible gene sets you want to search through, stored on seperate lines in a .txt file.
#--minOverlap: the minimum number of overlapping genes you want to filter your results by. optional: default is 0.

import json
import requests
import sys
import getopt
import operator

#Stores all data associated with one result from a database. toString method outputs to CSV-style format.
class Entry():
    def __init__(self , geneSet , term , overlapGenes , pval , zscore , adjPval , score , genes):
        self.geneSet = geneSet
        self.term = term
        self.overlapGenes = overlapGenes
        self.pval = pval
        self.zscore = zscore
        self.adjPval = adjPval
        self.score = score
        self.genes = genes
    def toString(self):
        return(self.geneSet + ',' + self.term + ',' + str(self.overlapGenes)+'_'+str(numGenes) + ',' + str(self.pval) + ',' + str(self.zscore) + ',' + str(self.adjPval) + ',' + str(self.score) + ',' + str(self.genes) + '\n')

#This will be appended to become a database of all Entries
entries = []

#Stores the name and a gene string from one module in the input file.
class Module():
    def __init__(self , name):
        self.name = name
        self.geneString = ''
        self.numGenes = 0
    def add(self , gene):
        self.geneString = self.geneString + gene + '\n'
        self.numGenes += 1
    def toString(self):
        return('Module Name: %s\n%s' % (self.name , self.geneString))


#this will be appended to become a database of all Modules
modules = []

#URL given by Enrichr for its upload API
postURL = 'http://amp.pharm.mssm.edu/Enrichr/addList'

#Parses options given with the program call from terminal.
#See comment at top of file for option list.
opts = getopt.getopt(sys.argv[1:] , '' , ['ifile=' , 'ofile=' , 'libraries=' , 'minOverlap='])

iFilePath = None
oFilePath = None
geneSetLibraries = []
minOverlap = None
for opt , arg in opts[0]:
    if opt == '--ifile':
        iFilePath = arg
        print 'iFilePath = ' + iFilePath
    elif opt == '--ofile':
        oFilePath = arg
        print 'oFilePath = ' + oFilePath
    elif opt == '--libraries':
        moreLibraries = True
        while moreLibraries:
            print geneSetLibraries
            if arg.find(',') > -1:
                geneSetLibraries.append(arg[:operator.indexOf(arg , ',')])
                arg = arg[(operator.indexOf(arg  , ',') + 1):]
            else:
                geneSetLibraries.append(arg)
                moreLibraries = False
    elif opt == '--minOverlap':
        minOverlap = arg
        print 'minOverlap = ' + minOverlap

if minOverlap is None:
    minOverlap = 0

if iFilePath is None or oFilePath is None or geneSetLibraries is []:
    raise Exception('Incorrect option syntax. See below for example:\n\npython enrichrAPI.py --ifile <iFilePath> --ofile <oFilePath> --libraries <libraryFilePath> [--minOverlap] <int>]')

#Read in genes and modules from the input file
ifile = open(iFilePath , 'r')
geneString = ''
numGenes = 0

for line in ifile:
    gene = line[:line.find('\t')]
    mod = line[(line.find('\t') + 1):]
    hasBeenPlaced = False
    for module in modules:
        if module.name == mod:
            module.add(gene)
            hasBeenPlaced = True
    if not hasBeenPlaced:
        newMod = Module(mod)
        newMod.add(gene)
        modules.append(newMod)

for module in modules:
    print(module.toString())

ofile = open(oFilePath , 'w')

#POST request to /Enrichr/addList to upload data
payload = {
    'list': (None, geneString)
}

print('Uploading data...')

response = requests.post(postURL , files=payload)
if not response.ok:
    raise Exception('Error analyzing gene list')

print('Data uploaded.')

uploadData = json.loads(response.text)

ofile.write('Gene Set,Term,Overlap,Pval,Z Score,Adjusted Pval,Combined Score,Genes\n')

#Iterates over all libraries in geneSetLibraries (list inputted by user), makes
# a GET call to Enrichr/enrich, and transfers all results into entries
for geneSetLibrary in geneSetLibraries:
    print('Searching %s...' % geneSetLibrary)

    response = requests.get('http://amp.pharm.mssm.edu/Enrichr/enrich?userListId=%s&backgroundType=%s' % (uploadData.get('userListId') , geneSetLibrary))

    if not response.ok:
        raise Exception('Error searching %s' % geneSetLibrary)

    data = json.loads(response.text)



    for database in data:
        for entry in data[database]:
            overlapGenes = ''
            for gene in entry[5]:
                overlapGenes += gene + ';'
            entries.append(Entry(database , entry[1] , len(entry[5]) , entry[2] , entry[3] , entry[6] , entry[4] , overlapGenes))

print('Libraries searched.')

#Sort entries by their combined score
sortedEntries = sorted(entries, key=lambda entry: entry.score , reverse=True)

#Iterate over entries and print each entry

for entry in sortedEntries:
    if int(entry.overlapGenes) >= int(minOverlap):
        ofile.write(entry.toString())

print('%s written.' % oFilePath)

ifile.close()
ofile.close()
