#### Céline Vanini
'''parse the $boot file to verify if the MFT file is '''


import struct
import logging
from argparse import ArgumentParser

boot_logger = logging.getLogger('boot')

def parse_boot(filename):
    with open(filename, 'rb') as file:
        data = file.read()

    boot_logger.info(f'OEM_ID : {struct.unpack("<Q", data[3:11])[0]}')
    boot_logger.info(f'Bytes per sector : {struct.unpack("<H", data[11:13])[0]}')
    boot_logger.info(f'Sectors per cluster : {struct.unpack("<B", data[13:14])[0]}')
    boot_logger.info(f'Sectors count on volume : {struct.unpack("<Q", data[40:48])[0]}')
    boot_logger.info(f'Cluster # of the start of the MFT : {struct.unpack("<Q", data[48:56])[0]}')
    boot_logger.info(f'Cluster # of the start of the MFTmirr : {struct.unpack("<Q", data[56:64])[0]}')
    entry_size = struct.unpack("<b", data[64:65])[0]
    if entry_size < 0:
        entry_size = -entry_size
        boot_logger.info(f'MFT entry size: : {(2**entry_size)}')
    else:
        boot_logger.info(f'MFT entry size: : {entry_size}')
    boot_logger.info(f'Volume Serial #: : {struct.unpack("<Q", data[72:80])[0]}')

def log(file):
    boot_logger.info('Starting to process the $Boot. Some informations about the volume :')
    parse_boot(file)
    boot_logger.info('Process finished !')


if __name__ == '__main__':
    parser = ArgumentParser(description='boot parser : used to catch volume informations')
    parser.add_argument('-f', '--file', help='boot file', required=True)
    args = parser.parse_args()

    # boot_logger.basicConfig(filename='process.txt', format='%(message)s', level=boot_logger.INFO)
    # boot_logger.info('Starting to process the $Boot. Some informations about the volume :')

    # parse_boot(args.file)
    # boot_logger.info('Process finished !')