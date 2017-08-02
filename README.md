# enrichrAPI
### Purpose
A python script for batch querying Enrichr, a gene enrichment database. Note: this project is in no way affiliated with Enrichr; it just uses its API.

### Files

- enrichrAPI.py: the actual script. See below for a list of options in the console call.
Pakages used: json, requests, sys, getopt, operator, xlswriter, time
- libraries.txt: the libraries that you want Enrichr to query.
Feel free to change the name of this file as long as you change the console call as well.
- sampleData: A folder containing a couple of test data sets.

### Calling the Script from the Console
`python enrichrAPI.py --ifile <iFilePath> --ofile <oFilePath> --libraries <libraryFilePath> [--sort <attribute>] [--minOverlap] <int>] [--minAdjPval <int>]`

`--ifile`: the file path for the input (.txt) file. should have two columns: first has gene names, second has corresponding modules

`--ofile`: the file path for the output (.xlsx) file with the Enrichr results

`--libraries`: the Enrichr-compatible gene sets you want to search through, stored on seperate lines in a .txt file.

`--sort`: the attribute by which to sort the results. Available attributes are listed below:

- `combinedScore`: (DEFAULT) sort high-to-low by the combined score of each result
- `geneSet`: sort alphabetically by the gene set database (i.e. library) that each result was found in
- `term`: sort alphabetically by term
- `overlapGenes`: sort high-to-low by the number of genes in the module overlapping with the result pathway
- `pval`: sort low-to-high by P-value
- `zscore`: sort low-to-high by Z-score
- `adjPval`: sort low-to-high by adjusted P-value
- `genes`: sort alphabetically by the list of genes involved in the result pathway (I have no clue why this would be helpful, but why not?)

`--minOverlap`: the minimum number of overlapping genes you want to filter your results by. optional: default is 5

`--minAdjPval`: genes with p values below this number will be removed from the results. optional: default is .05

### Gene List Input Formatting
Input your genes in .tsv format with two columns: column 0 for the gene name and column 1 for the module name. (If you only have 1 module, still put somehting in.)
See sampleData/genes2.txt for an example!

### Libraries File Formatting
Write the names of all Enrichr libraries you wish to query in a text file, separating each entry with a line break.

### Outputs
enrichrAPI.py uses the xlswriter package, so the program can output to .xls or .xlsx. Write the desired output filename as an option (see above).

Each module receives its own sheet in the excel output file. The results for all libraries are restricted to the given minimum overlaps and pvals, sorted
by their combined score, and written to the excel file like below:

|Gene Set|Term|Overlap|Pval|Z Score|Adjusted Pval|Combined Score|Genes|
|--------|----|-------|----|-------|-------------|--------------|-----|
GO_Biological_Process_2017|positive regulation of establishment of protein localization to telomere (GO:1904851)|5_9|0.0001568284606509318113154449747526086866855621337890625|0.7731966399939594|0.01099106128395280386478294332164296065457165241241455078125|-3.4876371667942454|CCT6A;CCT2;TCP1;CCT8;CCT5

### Known Issues
See the "Issues" page on this Github page for details.
