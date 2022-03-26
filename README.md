# Forensic-Tools

### Description
Suite de modules permettant de parser divers fichiers systèmes utilisés par NTFS : $boot, $bitmap et le $MFT. Les scripts sont orientés pour extraire les informations seulement nécessaires à la stratigraphie.
Notamment, dans le module MFT.py, certains attributs de la $MFT ne sont pas parsés.

### Usage 
python process.py -v *volume to be processed* -s *size* -n *stage*

Arguments supplémentaires : d (delete) et b (backdating)