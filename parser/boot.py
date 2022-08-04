#### Céline Vanini
'''parse the $boot file to verify if the MFT file is '''
import os
import csv
import struct
import logging
from pathlib import Path
from argparse import ArgumentParser

boot_logger = logging.getLogger('boot')


def parse_boot(filename):
    boot_logger.info('Starting to process the $Boot. Some informations about the volume :')

    with open(filename, 'rb') as file:
        data = file.read()

    boot = {}
    boot['OEM_ID'] = data[3:11].decode('utf-8')
    boot['Bytes per sector'] = struct.unpack("<H", data[11:13])[0]
    boot['Sectors per cluster'] = struct.unpack("<B", data[13:14])[0]
    boot['Sectors count on volume'] = struct.unpack("<Q", data[40:48])[0]
    boot['Cluster # of the start of the MFT'] = struct.unpack("<Q", data[48:56])[0]
    boot['Cluster # of the start of the MFTmirr'] = struct.unpack("<Q", data[56:64])[0]

    [boot_logger.info(f'{k} : {v}') for k, v in boot.items()]

    # size can be expressed in two different ways
    entry_size = struct.unpack("<b", data[64:65])[0]
    if entry_size < 0:
        entry_size = -entry_size
        boot_logger.info(f'MFT entry size: : {(2 ** entry_size)}')
        boot['MFT entry size'] = 2 ** entry_size
    else:
        boot_logger.info(f'MFT entry size: : {entry_size}')
        boot['MFT entry size'] = entry_size
    boot['Volume Serial #'] = struct.unpack("<Q", data[72:80])[0]
    boot_logger.info(f'Volume Serial #: : {struct.unpack("<Q", data[72:80])[0]}')
    boot_logger.info('Process finished !')

    return boot


# writes boot info into CSV file with 2 columns (Information/Value)
def boot_to_csv(dir, dict_boot):
    with open(f'{dir}\\boot.csv', 'w', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.DictWriter(csvfile, fieldnames=['Information', 'Value'])
        csvwriter.writeheader()
        for k, v in dict_boot.items():
            csvwriter.writerow({'Information': k, 'Value': v})


if __name__ == '__main__':
    parser = ArgumentParser(description='boot parser : used to catch volume informations')
    parser.add_argument('-f', '--file', help='boot file to be parsed', required=True)
    parser.add_argument('-o', '--output', help='output directory', required=True)
    parser.add_argument('-c', '--csv', help='saving information to csv file', required=False, action='store_true')

    args = parser.parse_args()
    args.output = Path(args.output)

    if not os.path.isdir(args.output):
        os.mkdir(args.output)

    logging.basicConfig(format='%(asctime)s - %(name)-12s: %(message)s',
                        datefmt='[%d.%m.%Y %H:%M:%S]', level=logging.INFO,
                        handlers=[logging.FileHandler(f'{args.output}\\boot.txt'), logging.StreamHandler()])

    boot = parse_boot(args.file)

    if args.csv:
        boot_to_csv(args.output, boot)

