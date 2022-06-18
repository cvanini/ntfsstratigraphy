# ntfs_stratigraphy

### Description

Forensic-tools is formed of several scripts that parse some of the major system file of NTFS ($Boot, $Bitmap and $MFT).
It uses the Sleuth Kit library created by Brian Carrier (Windows version) in order to extract the system files to be parsed from 
either an image file or a live volume.

The use of this library is as follows - for example to extract the $MFT from a live volume named D:

     <library_path>\icat.exe \\.\D: 0 > <destination_path>\$MFT

Note that on some volumes, the extraction has to be made on Safe Mode (otherwise the $MFT is filled with unwanted zeros). To
parse an image file you have to specify the offset of the start of the volume (which can be found with the .\mmls.exe command).


### Parser module
This module contains several scripts that can be used independently (specifically the parsers) if desired.

#### MFT.py
The MFT.py script is a MFT parser that focuses on some specific and useful attributes ($STANDARD_INFORMATION, $DATA and $FILE_NAME).
Some attributes are not parsed for now [to be completed]. Extracted information can be saved on both json (by default) or csv format. The json format saves every information while the csv one focuses only on
information that are useful to perform digital stratigraphy. 

Usage :

    python MFT.py -f <$MFT_file> -o <output_directory> -c 

Optional arguments : 
- c : save information in csv format. If not specified, information are saved in json format.
- p : if specified, reconstruct file paths on the volume. Note : is really time consuming when parsing large volumes.



#### bitmap.py
The bitmap.py script is a bitmap parser 

Usage :

    python bitmap.py -f <$Bitmap_file> -o <output_directory> -c 

Optional arguments : 
- c : save information in csv format.

#### boot.py
The boot.py script is a boot parser that save volume information on a text format (when used with process.py). 
Boot information can be saved independently on a csv file, if specified.

Usage :

    python boot.py -f <$Boot_file> -o <output_directory> -c 

Optional arguments : 
- c : save information in csv format. 


#### process.py

#### main.py


### Module process 
ss

Arguments : 
- v : volume live to be processed
- s : size of the file to be created on the volume. If not specified, files are created with a random size
- n : name of the stage (eg. 11042022_1)

Usage : python process.py -v *volume to be processed* -s *size* -n *stage*

