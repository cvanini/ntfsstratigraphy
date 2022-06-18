#### Céline Vanini
#### 02.03.2022

'''parse an image file and automatically extract system files, parses them, saves the extracted info in a csv or json
file'''

import os
import subprocess
from MFT import *
from boot import *
from bitmap import *
from ressources.MFT_utils import *
from argparse import ArgumentParser

logger = logging.getLogger('main')

curr = os.getcwd()
sleuthkit = f'{curr}\\sleuthkit\\bin\\'

def get_offset(image):
    subprocess.run(['mmls.exe', f'{image}'], cwd=sleuthkit, shell=True)
    offset = input("Please write the first offset of the partition to parse: ")
    return offset

def extract_from_image(offset, image, output):
    logger.info('Extracting $Bitmap, $Boot and $MFT')
    # Extracting and parsing the $boot to obtain volume information
    subprocess.run(['icat.exe', '-o', f'{offset}', '-f', 'ntfs', f'{image}', '7', '>', f"{output}\\$Boot"], cwd=sleuthkit, shell=True)
    # Parsing the $BITMAP attribute in the entry 0 of the $MFT (used for the MFT file itself..)
    # It contains the number of entries that are used in the $MFT, so can be compared with the result of the
    # MTF.py script, to be sure it parsed all entries.
    subprocess.run(['icat.exe', '-o', f'{offset}', '-f', 'ntfs', f'{image}', '0-176', '>', f"{output}\\MFT_bitmap"], cwd=sleuthkit, shell=True)
    # command to copy the $Bitmap of the specified volume (entry 6)
    subprocess.run(['icat.exe', '-o', f'{offset}', '-f', 'ntfs', f'{image}', '6', '>', f"{output}\\$Bitmap"], cwd=sleuthkit, shell=True)
    # command to copy the $MFT of the specified volume (entry 0)
    subprocess.run(['icat.exe', '-o', f'{offset}', '-f', 'ntfs', f'{image}', '0', '>', f"{output}\\$MFT"], cwd=sleuthkit, shell=True)

########################################################################################################################
# WORK IN PROGRESS
# Add a hash comparison with the NSRL database to flag system files

def listing_files(database, offset, image, output):
    logger.info('Starting the flagging of system files on the volume')

    logger.info('Listing files')
    subprocess.run(['fls.exe', '-r', '-o', f'{offset}', f'{image}', '>', f"{output}\\temp_file_list.txt"],
                   cwd=sleuthkit, shell=True)

    inodes = []
    with open(f'{output}\\temp_file_list.txt', 'r') as file:
        data = file.readlines()

        for line in data:
            temp = line.split(': ')[0]
            inodes.append(temp.split(' ')[-1])

    with open(f'{output}\\attributes_file_list.txt', 'w') as file:
        file.write('\n'.join([x for x in inodes]))

    # subprocess.run('Get-Content', f'${output}\\temp_file_list.txt', '|', 'ForEach-Object', '{$_.split(":")[0].split(" ")[-1]}', '>', f'{output}\\file_list_inode.txt')


def hashing(file_list, offset, image, output):
    # TODO: problème c'est d'avoir le hash de tous les fichiers d'une image
    # with open(f'{output}\\{file_list}', 'r') as file:
    #     data = file.readlines()
    #
    #     for file in data:
    #         subprocess.run(['icat.exe', '-o', f'{offset}', f'{image}', '>', f"{output}\\temp.txt"],
    #                        cwd=sleuthkit, shell=True)
    pass

# TODO: include database in the parser
def nsrl(database, offset, image, output):

    pass
    # TODO: indexer la base de données
    # TODO: filtrer NSRL pour avoir que les OS Windows ?
    # TODO: hfind sur la liste de fichiers, retourner genre une liste de 0 et 1 par inode ?
    # TODO: ajouter ça au dico de la MFT dans genre le header MFT['Is a file system']



if __name__ == '__main__':
    parser = ArgumentParser(description='Image file parser : extract system files and parse them to product csv files')
    parser.add_argument('-f', '--file', help='image file', required=True)
    parser.add_argument('-o', '--output', help='output directory for the created files', required=True)
    # parser.add_argument('-n', '-nsrl', help='path to the NSRL database file', required=False)

    args = parser.parse_args()

    if not os.path.isdir(args.output):
        os.mkdir(args.output)

    logging.basicConfig(format='%(asctime)s - %(name)-12s: %(message)s',
                        datefmt='[%d.%m.%Y %H:%M:%S]', level=logging.INFO,
                        handlers=[logging.FileHandler(f'{args.output}\\parsing.txt'), logging.StreamHandler()])

    logger.info('Starting to process')

    offset = get_offset(args.file)
    extract_from_image(offset, args.file, args.output)

    boot = parse_boot(f"{args.output}\\$Boot")
    boot_to_csv(args.output, boot)

    MFT = parse_MFT(f"{args.output}\\$MFT")
    MFT_to_csv(args.output, MFT)
    len_MFT = parse_bitmap_MFT(f"{args.output}")
    if len_MFT != len(MFT):
        logger.info(f'Warning : {len_MFT} entries ($BITMAP in entry 0) vs {len(MFT)} entries (extracted from code)')

    bitmap = parse_bitmap(f"{args.output}\\$Bitmap")
    bitmap_to_csv(args.output, bitmap)

    logger.info('Main process finished !')


