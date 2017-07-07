#enrichrAPI.py
#Russell Stewart
#7/7/2017
#Allows a user to specify a .txt file of genes, an output file, and a list of
#gene sets to batch analyze in Enrichr, eliminating the need for using UIs with
#the website.
#
#PROGRAM OPTIONS:
#python enrichrAPI.py --ifile <iFilePath> --ofile <oFilePath> --libraries <libraryFilePath> [--minOverlap] <int>] [--minAdjPval <int>]
#--ifile: the file path for the input (.txt) file. should have two columns: first has gene names, second has corresponding modules
#--ofile: the file path for the output (.xlsx) file with the Enrichr results
#--libraries: the Enrichr-compatible gene sets you want to search through, stored on seperate lines in a .txt file.
#--minOverlap: the minimum number of overlapping genes you want to filter your results by. optional: default is 5
#--minAdjPval: genes with p values below this number will be removed from the results. optional: default is .05
#
#FUTURE FEATURES:
#Pval cutoff
#Something seems to be wrong with gene overlap numbers (like we're getting 100 overlaps out of 30 genes)

import json
import requests
import sys
import getopt
import operator
import xlsxwriter

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
        return('Module Name: %s\nNum. Genes:%d\n%s' % (self.name , self.numGenes , self.geneString))


#this will be appended to become a database of all Modules
modules = []

#URL given by Enrichr for its upload API
postURL = 'http://amp.pharm.mssm.edu/Enrichr/addList'

#Parses options given with the program call from terminal.
#See comment at top of file for option list.
opts = getopt.getopt(sys.argv[1:] , '' , ['ifile=' , 'ofile=' , 'libraries=' , 'minOverlap=' , 'minAdjPval='])

iFilePath = None
oFilePath = None
geneSetLibraries = []
minOverlap = None
minAdjPval = None
for opt , arg in opts[0]:
    if opt == '--ifile':
        iFilePath = arg
    elif opt == '--ofile':
        oFilePath = arg
    elif opt == '--libraries':
        libraryFile = open(arg , 'r')
        for line in libraryFile:
            geneSetLibraries.append(line[:line.find('\n')])
    elif opt == '--minOverlap':
        minOverlap = arg
    elif opt == '--minAdjPval':
        minAdjPval = arg

if minOverlap is None:
    minOverlap = 5

if minAdjPval is None:
    minAdjPval = .05

if iFilePath is None or oFilePath is None or geneSetLibraries is []:
    raise Exception('Incorrect option syntax. See below for example:\n\npython enrichrAPI.py --ifile <iFilePath> --ofile <oFilePath> --libraries <libraryFilePath> [--minOverlap] <int>] [--minAdjPval <int>]')

#Read in genes and modules from the input file
ifile = open(iFilePath , 'r')
geneString = ''
numGenes = 0

for line in ifile:
    gene = line[:line.find('\t')]
    mod = line[(line.find('\t') + 1):line.find('\n')]
    if mod != 'module':
        hasBeenPlaced = False
        for module in modules:
            if module.name == mod:
                module.add(gene)
                hasBeenPlaced = True
        if not hasBeenPlaced:
            newMod = Module(mod)
            newMod.add(gene)
            modules.append(newMod)

ofile = xlsxwriter.Workbook(oFilePath)

#go through ENRICHR API dance once per module, and add enriched data to ofile
for module in modules:
    print '\nEnriching module %s' % module.name

    #Worksheet setup
    worksheet = ofile.add_worksheet(module.name)
    worksheet.write(0 , 0 , 'Gene Set')
    worksheet.write(0 , 1 , 'Term')
    worksheet.write(0 , 2 , 'Overlap')
    worksheet.write(0 , 3 , 'Pval')
    worksheet.write(0 , 4 , 'Z Score')
    worksheet.write(0 , 5 , 'Adjusted Pval')
    worksheet.write(0 , 6 , 'Combined Score')
    worksheet.write(0 , 7 , 'Genes')


    #This will be appended to become a database of all Entries.
    entries = []

    #POST request to /Enrichr/addList to upload data
    payload = {
        'list': (None, module.geneString)
    }

    print('Uploading data...')

    response = requests.post(postURL , files=payload)
    if not response.ok:
        raise Exception('Error analyzing gene list')

    print('Data uploaded.')

    uploadData = json.loads(response.text)


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

    row = 1
    for entry in sortedEntries:
        if int(entry.overlapGenes) >= int(minOverlap) and int(entry.adjPval) >= int(minAdjPval):
            worksheet.write(row , 0 , entry.geneSet)
            worksheet.write(row , 1 , entry.term)
            worksheet.write(row , 2 , str(entry.overlapGenes)+'_'+str(module.numGenes))
            worksheet.write(row , 3 , entry.pval)
            worksheet.write(row , 4 , entry.zscore)
            worksheet.write(row , 5 , entry.adjPval)
            worksheet.write(row , 6 , entry.score)
            worksheet.write(row , 7 , entry.genes)
            row += 1

    print '%s written.' % module.name

print '\nSaving %s...' % oFilePath

ifile.close()
ofile.close()

print '\n\n%s written. All done!' % oFilePath
