# [Ongoing project] Forensic-Tools

### Description
Module suite specifically created for a master thesis on NTFS digital stratigraphy. 

Forensic-tools is formed of serveral script that parse some of the major system file of NTFS ($Boot, $Bitmap and $MFT). As it is an ongoing project, it is not yet made for public usage as a whole, but each parser can be used separately. As an example the MFT.py module only parses attributes of interest from the Master File Table for the thesis and extract the information that can be used to visualize the cluster allocation of the file system and perform digital stratigraphy.

- MFT.py : $MFT parser
- boot.py : $boot parser, used to extract information related to the volume being of concern + help to check if the MFT.py parser gets the right number of entries in the $MFT.
-  bitmap.py



### Usage 
python process.py -v *volume to be processed* -s *size* -n *stage*

