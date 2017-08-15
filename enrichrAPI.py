#enrichrAPI.py
#Russell Stewart
#7/7/2017
#Allows a user to specify a .txt file of genes, an output file, and a list of
#gene sets to batch analyze in Enrichr, eliminating the need for using UIs with
#the website.
#
#PROGRAM OPTIONS:
#python enrichrAPI.py --ifile <iFilePath> --ofile <oFilePath> --libraries <libraryFilePath> [--sumarize --threads <int>] [--sort <attribute>] [--minOverlap] <int>] [--minAdjPval <int>]
#--ifile: the file path for the input (.txt) file. should have two columns: first has gene names, second has corresponding modules
#--ofile: the file path for the output (.xlsx) file with the Enrichr results
#--libraries: the Enrichr-compatible gene sets you want to search through, stored on seperate lines in a .txt file.
#--sumarize: if specified, generate a summary sheet with the most-mentioned genes, diseases, and anatomical features for each module.
#--threads: Use if --summarize is used! The number of threads available on your processor for named entity recognition. Default: 1
#--minOverlap: the minimum number of overlapping genes you want to filter your results by. optional: default is 5
#--minAdjPval: genes with p values below this number will be removed from the results. optional: default is .05
#--sort: Sort results by one of following attributes:
#"geneSet" , "term" , "overlapGenes" , "pval" , "zscore" , "adjPval" , "genes" , "combinedScore" (default)
#
import json
import requests
import sys
import os
import getopt
import operator
import xlsxwriter
import time
import operator

#Stores all data associated with one result from a database. toString method outputs to CSV-style format.
class Entry():
    def __init__(self , geneSet , term , overlapGenes , pval , zscore , adjPval , score , genes):
        self.geneSet = geneSet
        self.term = term
        self.overlapGenes = overlapGenes
        #Only cast if the entry isn't a header column in the csv sent by Enrichr
        if overlapGenes.find('Overla') == -1:
            self.overlapGenesInt = int(overlapGenes[:overlapGenes.find('_')])#overlapGenesInt is only used for sorting purposes.
            self.pval = float(pval)
            self.zscore = float(zscore)
            self.adjPval = float(adjPval)
            self.score = float(score)
        else:
            self.overlapGenesInt = None
            self.pval = None
            self.zscore = None
            self.adjPval = None
            self.score = None
        self.genes = genes
    def toString(self):
        return(self.geneSet + ',' + self.term + ',' + str(self.overlapGenes) + ',' + str(self.pval) + ',' + str(self.zscore) + ',' + str(self.adjPval) + ',' + str(self.score) + ',' + str(self.genes) + '\n')

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

# creates new directory
# args:
#       dir_path - directory location of new folder
#       dir_name - name of new directory
# returns:
#       newly created directory
def makeDir(dir_path, dir_name):
    print 'dir path:' + dir_path
    print 'dir name:' + dir_name
    new_dir = os.path.join(dir_path,dir_name)
    print new_dir
    if not os.path.isdir(new_dir):
            os.mkdir(new_dir)
            return(new_dir)
    return(new_dir)

#Reads the text of the HTTP response (which returns a .txt file), removes any
#non-ascii characters, then parses the response into individual Entry classes and
#appends these to entries
#inputs:
#response: the response from the API GET call
#geneSetLibrary: the name of the library (to put in the spreadsheet)
#entries: the instance of xlswriter for the ouptut file
def parseResults(response , geneSetLibrary , entries):
    #parse response into a string and remove any non-ascii characters, replacing them with ' '
    #(we were having some issues with reactome_2016 throwing us non-unicode characters lol)
    fileBody = ''
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            try:
                chunk.decode('utf_8')
                fileBody += chunk
            except:
                print("  Non-ascii characters detected. I'll fix it...")
                x = ''
                for char in chunk:
                    if ord(char) > 127:
                        x += ' '
                    else:
                        x += char
                fileBody += x

    shouldLoop = 1
    while shouldLoop:
        term = fileBody[:fileBody.find('\t')]
        fileBody = fileBody[(fileBody.find('\t') + 1):]
        overlap = fileBody[:fileBody.find('\t')]
        overlap = overlap[:overlap.find('/')] + '_' + overlap[(overlap.find('/') + 1):]
        fileBody = fileBody[(fileBody.find('\t') + 1):]
        Pval = fileBody[:fileBody.find('\t')]
        fileBody = fileBody[(fileBody.find('\t') + 1):]
        adjPval = fileBody[:fileBody.find('\t')]
        fileBody = fileBody[(fileBody.find('\t') + 1):]
        oldPval = fileBody[:fileBody.find('\t')]
        fileBody = fileBody[(fileBody.find('\t') + 1):]
        oldAdjPval = fileBody[:fileBody.find('\t')]
        fileBody = fileBody[(fileBody.find('\t') + 1):]
        Zscore = fileBody[:fileBody.find('\t')]
        fileBody = fileBody[(fileBody.find('\t') + 1):]
        score = fileBody[:fileBody.find('\t')]
        fileBody = fileBody[(fileBody.find('\t') + 1):]
        genes = fileBody[:fileBody.find('\n')]
        fileBody = fileBody[(fileBody.find('\n') + 1):]
        if len(fileBody) > 1:
            shouldLoop = True
        else:
            shouldLoop = False
        newEntry = Entry(geneSetLibrary , term , overlap , Pval , Zscore , adjPval , score , genes)
        entries.append(newEntry)

#this function runs named entity recognition and generates a summary sheet
#if the --sumarize option is used.
def namedEntityRecognition(entries , ofile , nerPath , threads , workbook):
    #extract a file path to be used for temporary output files from ofile's
    #path
    i = 0
    loop = True
    index = -1
    while loop:
        if ofile[i] == '/':
            index = i
        i += 1
        if i >= len(ofile):
            loop = False
    new_ofilepath = ofile[:index]
    makeDir(new_ofilepath , 'enrichrAPI_temp')
    #write each module's terms to its own text file (for use with neji)
    for module , terms in entries.items():
        terms = '\n'.join(terms)
        temp = ''
        for i in range(0 , len(terms)):
            if terms[i] == '_':
                temp += ' '
            else:
                temp += terms[i]

        file = open('%s/enrichrAPI_temp/%s.txt' % (new_ofilepath , module) , 'w')
        file.write(temp)
        file.close()

    #run neji named entity recognition on the files generated above
    print '\nRunning NER on terms...'
    cwd = os.getcwd()
    os.chdir(nerPath)
    command = '%s/neji.sh -i %s -o %s -d %s/resources/dictionaries -m %s/resources/models -t %d -if RAW -of JSON' %(nerPath , new_ofilepath + '/enrichrAPI_temp' , new_ofilepath + '/enrichrAPI_temp' , nerPath , nerPath , threads)
    print '\n' + command + '\n'
    returncode = os.system(command)

    #sort through the neji output files for the most common classifications
    #in each module's enrichr term corpus
    print 'Opening NER output files...'
    os.chdir(new_ofilepath + '/enrichrAPI_temp')
    k = 0
    j = 0
    worksheet = workbook.add_worksheet('Summary')

    #get only neji's output (json) files
    filenames = [filename for filename in os.listdir(os.getcwd()) if filename.find('json') > -1]
    print 'Generating summary sheet...'
    #iterate over each file (1 file = 1 module)
    for filename in filenames:
        classifications = {}
        nerFile = json.loads(open(filename , 'r').read())
        #put all classifications from the json file into the classifications
        #database.
        for sentence in nerFile:
            for term in sentence['terms']:
                classification = term['ids']
                i = 0
                while i < len(classification):
                    if classification[i] == ':':
                        classification = classification[(i + 1):]
                        i = -1
                    if classification[i] == '|' or classification[i] == ')':
                        classification = classification[:i]
                        i = len(classification)
                    i+= 1
                if not classification in classifications:
                    classifications[classification] = {term['text'] : 1}
                else:
                    if not term['text'] in classifications[classification]:
                        classifications[classification][term['text']] = 1
                    else:
                        classifications[classification][term['text']] += 1
        #write the name of the current module to the file
        worksheet.write(k , j , filename[:filename.find('.')])
        k += 1
        #iterate over the 3 classifications given by neji in classications {}
        #(genes, anatomy, and diseases)
        for classification , terms in classifications.items():
            #write type of classification (genes, anatomy, or diseases)
            if classification == 'PRGE':
                classification = 'genes'
            elif classification == 'ANAT':
                classification = 'anatomy'
            elif classification == 'DISO':
                classification = 'diseases'
            worksheet.write(k , j , classification)
            #write the 10 most-mentioned classifications
            for term in sorted(terms , key = operator.itemgetter(1) , reverse = True):
                j += 1
                worksheet.write(k  , j , term)
                if j > 11:
                    break
            k += 1
            j = 0
    #remove all of the temp files
    os.chdir(new_ofilepath)
    os.system('rm -rf enrichrAPI_temp')


#this will be appended to become a database of all Modules
modules = []

#URL given by Enrichr for its upload API
postURL = 'http://amp.pharm.mssm.edu/Enrichr/addList'

#Parses options given with the program call from terminal.
#See comment at top of file for option list.
opts = getopt.getopt(sys.argv[1:] , '' , ['ifile=' , 'ofile=' , 'libraries=' , 'minOverlap=' , 'minAdjPval=' , 'sort=' , 'sumarize' , 'threads'])

iFilePath = None
oFilePath = None
geneSetLibraries = []
minOverlap = 5
minAdjPval = .05
ner = False
threads = 1
sort = 'combinedScore'
for opt , arg in opts[0]:
    if opt == '--ifile':
        iFilePath = arg
    elif opt == '--ofile':
        oFilePath = arg
    elif opt == '--libraries':
	    geneSetLibraries = [line.rstrip('\n') for line in open(arg, 'r')]
    elif opt == '--minOverlap':
        minOverlap = arg
    elif opt == '--minAdjPval':
        minAdjPval = arg
    elif opt == '--sort':
        sort = arg
    elif opt == '--sumarize':
        ner = True
    elif opt == '--threads':
        threads = arg

if iFilePath is None or oFilePath is None or geneSetLibraries is []:
    raise Exception('Incorrect option syntax. See below for example:\n\npython enrichrAPI.py --ifile <iFilePath> --ofile <oFilePath> --libraries <libraryFilePath> [--sumarize --threads <int>] [--sort <attribute>] [--minOverlap] <int>] [--minAdjPval <int>]\n')

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

#this database will store each module and a list of its resulting enrichr terms.
#only used if --summary is specified
if ner:
    lotsOfEntries = {}

#go through ENRICHR API dance once per module, and add enriched data to ofile
for module in modules:
    print('\nEnriching module %s' % module.name)

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

        url = 'http://amp.pharm.mssm.edu/Enrichr/export?userListId=%s&filename=%s&backgroundType=%s' % (uploadData.get('userListId') , 'exportResults' , geneSetLibrary)
        response = requests.get(url)
        #Attempts to search a 2015 version instead of the 20-- version if one
        #library search fails. If the older search fails too, it skips over
        #that module/library combination and moves on.
        if not response.ok:
            print('  Error searching %s' % geneSetLibrary)
            index = geneSetLibrary.find('20')
            if index > -1:
                geneSetLibrary = geneSetLibrary[:index] + '2015'
                print('  Trying %s instead...' % geneSetLibrary)
                url = 'http://amp.pharm.mssm.edu/Enrichr/export?userListId=%s&filename=%s&backgroundType=%s' % (uploadData.get('userListId') , 'exportResults' , geneSetLibrary)
                response = requests.get(url)
                if not response.ok:
                    print("Couldn't search %s (an older version). Skipping." % geneSetLibrary)
                else:
                    parseResults(response , geneSetLibrary , entries)
            else:
                print('  Could not search a previous version of %s. Skipping.' % geneSetLibrary)
        else:
            parseResults(response , geneSetLibrary , entries)

    print('Libraries searched.')

    #Sort entries by the user-specified attribute
    #"geneSet" , "term" , "overlapGenes" , "pval" , "zscore" , "adjPval" , "genes" , "combinedScore" (default)
    if sort == 'geneSet' or sort == 'geneset' or sort == 'GeneSet':
        sortedEntries = sorted(entries , key=lambda entry: entry.geneSet)
    elif sort == 'term' or sort == 'Term':
        sortedEntries = sorted(entries , key=lambda entry: entry.term)
    elif sort == 'overlapGenes' or sort == 'OverlapGenes' or sort == 'overlapgenes':
        sortedEntries = sorted(entries , key=lambda entry: entry.overlapGenesInt , reverse=True)
    elif sort == 'pval' or sort == 'Pval':
        sortedEntries = sorted(entries , key=lambda entry: entry.pval)
    elif sort == 'zscore' or sort == 'Zscore':
        sortedEntries = sorted(entries , key=lambda entry: entry.zscore)
    elif sort == 'adjPval' or sort == 'adjustedPval' or sort == 'AdjustedPval' or sort == 'AdjPval' or sort == 'adjustedpval' or sort == 'adjpval':
        sortedEntries = sorted(entries , key=lambda entry: entry.adjPval)
    elif sort == 'genes' or sort == 'Genes':
        sortedEntries = sorted(entries , key=lambda entry: entry.genes)
    else:#sort by combined score (default)
        sortedEntries = sorted(entries, key=lambda entry: entry.score , reverse=True)

    #Iterate over entries and print each entry
    row = 1
    for entry in sortedEntries:
        if entry.genes != 'Genes' and int(entry.overlapGenes[:entry.overlapGenes.find('_')]) >= int(minOverlap) and float(entry.adjPval) <= float(minAdjPval):
            worksheet.write_string(row , 0 , entry.geneSet)
            worksheet.write_string(row , 1 , entry.term)
            worksheet.write_string(row , 2 , str(entry.overlapGenes))
            worksheet.write_number(row , 3 , float(entry.pval))
            worksheet.write_number(row , 4 , float(entry.zscore))
            worksheet.write_number(row , 5 , float(entry.adjPval))
            worksheet.write_number(row , 6 , float(entry.score))
            worksheet.write_string(row , 7 , entry.genes)
            row += 1
    #update lotsOfEntries if --summary is specified
    if ner:
        lotsOfEntries[module.name] = [entry.term for entry in entries]
    print('%s written.' % module.name)

#run named entity recognition/generate summary sheet if --summary is specified
if ner:
    namedEntityRecognition(lotsOfEntries , oFilePath , '/Users/russellstewart/Documents/NationalJewish/Seibold/neji' , 4 , ofile)

#Close ifile and ofile
print('\nSaving %s...' % oFilePath)
ifile.close()
ofile.close()

print('\n\n%s written. All done!' % oFilePath)
