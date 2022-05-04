import os
import time
import bitmap, boot, MFT, process
import random
import shutil
import logging
import subprocess
from ressources.MFT_utils import *
from datetime import datetime, timedelta
from argparse import ArgumentParser


if __name__ == '__main__':
    # TODO: add image file support (create main.py?)
    parser = ArgumentParser()
    parser.add_argument('-s', '--size',
                        help='Size of the file to be created (in bytes), if not specified, creates files of random size',
                        type=int, required=False)
    parser.add_argument('-v', '--volume', help='Volume to process (i.e C:)', type=str, required=True)
    parser.add_argument('-n', '--stage', help='Stage of the test being processed (i.e 1_creation)', type=str,
                        required=True)
    parser.add_argument('-i', '--image', help='image file to analyze', required=False)
    # parser.add_argument('-o', '--output', help='Destination directory for the $MFT and $bitmap files', required=True)
    args = parser.parse_args()

    curr = os.getcwd()
    os.mkdir(f'{curr}\\data\\{args.stage}')

    logging.basicConfig(filename=f'{curr}\\data\\{args.stage}\\process.txt',
                        format='%(asctime)s - %(name)-12s: %(message)s',
                        datefmt='[%d.%m.%Y %H:%M:%S]', level=logging.INFO)
    logger = logging.getLogger('process')
    logger.info('Starting to process')
    logger.info(f'Current stage : {args.stage}')

    total, used, free = shutil.disk_usage(args.volume)
    logger.info(f'The volume has a capacity of {total} bytes')
    logger.info('Extracting $Bitmap, $Boot and $MFT at blank')
    process.extract(args.volume, args.stage, 0)
