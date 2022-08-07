# ntfsstratigraphy

### Description

This module is composed of several scripts that parse some of the major system file of NTFS ($Boot, $Bitmap and $MFT).
It uses the Sleuth Kit library created by Brian Carrier (Windows version) in order to extract the system files to be parsed from 
either an image file or a live volume.

The use of this library is as follows - for example to extract the $MFT from a live volume named D:

     <library_path>\icat.exe \\.\D: 0 > <destination_path>\$MFT

Note that on some volumes, the extraction has to be made on Safe Mode (otherwise the $MFT is filled with unwanted zeros) and with administrator rights. To
parse an image file you have to specify the offset of the start of the volume (which can be found with the .\mmls.exe command).


### Parser module
This module contains several scripts that can be used independently (specifically the parsers) if desired.

#### MFT.py
The MFT.py script is a MFT parser that focuses on some specific and useful attributes.
Some attributes are not parsed for now [to be completed]. Extracted information can be saved on both json (by default) or csv format. The json format saves every information while the csv focuses only on
information that are useful to perform digital stratigraphy. 

Usage :

    python MFT.py -f <$MFT_file> -o <output_directory>  

Optional arguments : 
- c : saves results in csv format. If not specified, information are saved in json format.
- p : if specified, reconstructs file paths on the volume. Note : is really time consuming when parsing large volumes (multiple hours).



#### bitmap.py
The bitmap.py script parses the $Bitmap and saves in a CSV file each cluster and its status on the volume being analyzed. 

Usage :

    python bitmap.py -f <$Bitmap_file> -o <output_directory>



#### boot.py
The boot.py script is a boot parser that saves volume information on a text format. 
Boot information can be saved independently on a csv file, if specified.

Usage :

    python boot.py -f <$Boot_file> -o <output_directory> 

Optional arguments : 
- c : save information in csv format. 


#### process.py
This script is used to perform actions on a test and live volume. You can spec
Usage :

    python process.py -v <volume e.g. D:> -n <stage> 

Optional arguments : 
- s : size of the file to be created on the volume. If not specified, files are created with a random size

#### main.py
Main script used to parse image files. It automatically extracts the system files, parses them with the help of the previously mentionned parsers and saves everything in CSV format.

Usage :

    python main.py -f <E01 file> -o <output_directory> 

Optional arguments : 
- j : saves results in json format. If not specified, information are saved in csv format.
- p : if specified, reconstructs file paths on the volume. Note : is really time consuming when parsing large volumes (multiple hours).

### Report module 
#### rules.py
This script produces pre-analysed files for stratigraphy analysis (events.txt which registers detected actions and two interactive graphs). A directory containing the output created
by the parser module (plus the NSRL flagged hash_list) is given as an input (mandatory files : MFT.csv, boot.csv and hash_list.csv)

Usage :

    python rules.py -d <directory> -o <output_directory> 

#### app.py
Deprecated