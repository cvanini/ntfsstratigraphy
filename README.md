# [Ongoing project] Forensic-Tools

### Description
Module suite specifically created for a master thesis on NTFS digital stratigraphy. 

Forensic-tools is formed of several scripts that parse some of the major system file of NTFS ($Boot, $Bitmap and $MFT). 

### Module MFT
$MFT parser. 

Arguments : 
- f : 
- c : 
- j :

Usage : python MFT.py -f *file* 

### Module bitmap

Usage : 

### Module boot
The script saves a boot.txt file in the specified output directory containing the 
information extracted from the $boot file given.

Usage : python .\boot.py -f *path to $boot file* -o *output directory*

### Module process 
ss

Arguments : 
- v : volume live to be processed
- s : size of the file to be created on the volume. If not specified, files are created with a random size
- n : name of the stage (eg. 11042022_1)

Usage : python process.py -v *volume to be processed* -s *size* -n *stage*

