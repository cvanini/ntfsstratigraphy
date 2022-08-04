#### Céline Vanini
#### 02.03.2022

'''parse an image file and automatically extract system files, parses them, saves the extracted info in a csv or json
file'''

import os, sys
import subprocess
from MFT import *
from boot import *
from bitmap import *
from pathlib import Path
from ressources.MFT_utils import *
from argparse import ArgumentParser

logger = logging.getLogger('main')

curr = os.getcwd()
sleuthkit = f'{curr}\\sleuthkit\\bin\\'

# The icat command requiring the offset of the partition on which you want to extract files, it executes at first
# the mmls command to display the offset of the beginning of each partition and ask the user to specify it
def get_offset(image):
    subprocess.run(['mmls.exe', f'{image}'], cwd=sleuthkit, shell=True)
    print(f'If nothing is displayed, offset is 0\n')
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



if __name__ == '__main__':
    parser = ArgumentParser(description='Image file parser : extract system files and parse them to product csv files')
    parser.add_argument('-f', '--file', help='image file - please enter the entire file path as the current directory while processing commands on Powershell is .\parser\sleuthkit', required=True)
    parser.add_argument('-o', '--output', help='output directory for the created files', required=True)
    parser.add_argument('-j', '--json', help='output MFT content into a json file', required=False, action='store_true')
    # parser.add_argument('-n', '-nsrl', help='path to the NSRL database file', required=False)

    args = parser.parse_args()

    if not os.path.isdir(args.output):
        os.mkdir(args.output)

    logging.basicConfig(format='%(asctime)s - %(name)-12s: %(message)s',
                        datefmt='[%d.%m.%Y %H:%M:%S]', level=logging.INFO,
                        handlers=[logging.FileHandler(f'{args.output}\\parsing.txt'), logging.StreamHandler()])

    logger.info('Starting to process')

    file = Path(args.file)
    if file.exists():
        offset = get_offset(file)
        extract_from_image(offset, args.file, Path(args.output))
    else:
        raise Exception(f'No such file or directory: {file}')

    # parsing $Boot at first and saving to CSV
    boot = parse_boot(f"{args.output}\\$Boot")
    boot_to_csv(args.output, boot)

    # then MFT in csv or json depending on the humor
    MFT = parse_MFT(f"{args.output}\\$MFT")
    if args.json:
        MFT_to_json(args.output, MFT)
    else:
        MFT_to_csv(args.output, MFT)

    # checking the number of entries
    len_MFT = parse_bitmap_MFT(f"{args.output}")
    if len_MFT != len(MFT):
        logger.info(f'Warning : {len_MFT} entries ($BITMAP in entry 0) vs {len(MFT)} entries (extracted from code)')

    # Finally the $Bitmap
    bitmap = parse_bitmap(f"{args.output}\\$Bitmap")
    bitmap_to_csv(args.output, bitmap)

    logger.info('Main process finished !')


