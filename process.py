#### Céline Vanini
#### Main module processing the experiment from creating files to extract system files of interest

# The script must be executed as administrator in a Powershell console !
# Do not run it on your volume ! It would be overwritten :)
# python .\process.py -v "C:" -n "1" -s 10

import os
import MFT
import time
import boot
import bitmap
import random
import shutil
import logging
import subprocess
from datetime import datetime, timedelta
from argparse import ArgumentParser


def extract(volume, stage, n):
    curr = os.getcwd()
    os.mkdir(os.getcwd() + f'\\data\\{stage}\\{str(n)}')

    # Extracting and parsing the $boot to obtain volume information
    if n == 0:
        subprocess.run(['icat.exe', f'\\\\.\\{volume}', '7', '>', f"{curr}\\data\\{stage}\\{str(n)}\\$Boot"],
                       cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)
        boot.log(f'{curr}\\data\\{stage}\\{str(n)}\\$Boot')

    # Parsing the $BITMAP attribute in the entry 0 of the $MFT (used for the MFT file itself..)
    # It contains the number of entries that are used in the $MFT, so can be compared with the result of the
    # MTF.py script, to be sure it parsed all entries.
    subprocess.run(['icat.exe', f'\\\\.\\{volume}', '0-176', '>', f"{curr}\\data\\{stage}\\{str(n)}\\MFT_bitmap"],
                   cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)
    # command to copy the $Bitmap of the specified volume (entry 6) and parse it with the bitmap.py python script
    subprocess.run(['icat.exe', f'\\\\.\\{volume}', '6', '>', f"{curr}\\data\\{stage}\\{str(n)}\\$Bitmap"],
                   cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)
    bitmap.log(f"{curr}\\data\\{stage}", n)
    # command to copy the $MFT of the specified volume (entry 0) and parse it with the MFT.py python script
    subprocess.run(['icat.exe', f'\\\\.\\{volume}', '0', '>', f"{curr}\\data\\{stage}\\{str(n)}\\$MFT"],
                   cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)
    MFT.log(f"{curr}\\data\\{stage}", n)


def extract_USN_logfile(volume, stage):
    curr = os.getcwd()
    subprocess.run(['icat.exe', f'\\\\.\\{volume}', '11', '>', f"{curr}\\data\\{stage}\\USN_journal"],
                   cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)
    subprocess.run(['icat.exe', f'\\\\.\\{volume}', '2', '>', f"{curr}\\data\\{stage}\\$LogFile"],
                   cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)

# create files of the specified size, in bytes.
def create(path, size):
    with open(str(path) + '.txt', 'wb') as file:
        # megabytes : file.write(b'0' * size * 1024 * 1024)
        file.write(b'0' * size)

        # flushing internal buffers and force write to disk
        file.flush()
        os.fsync(file.fileno())


def delete(path, filename):
    if os.path.exists(path + "\\" + filename):
        # os.remove(path + "\\" + filename)
        subprocess.run([f"del {path}\\{filename}"], shell=True)


# manipulating timestamps with Powershell command lines
def backdating(path):
    file = os.listdir(path)[-1]
    d = datetime.now(None) - timedelta(minutes=15)
    d = datetime.strftime(d, "%d.%m.%Y %H:%M:%S")

    if file.endswith('.txt'):
        subprocess.run([f"$(Get-Item {file}).creationtime=$(Get-Date \"{d}\")"], shell=True)
        subprocess.run([f"$(Get-Item {file}).lastaccesstime=$(Get-Date \"{d}\")"], shell=True)
        subprocess.run([f"$(Get-Item {file}).lastwritetime=$(Get-Date \"{d}\")"], shell=True)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-s', '--size', help='Size of the file to be created (in bytes), if not specified, creates files of random size',
                        type=int, required=False)
    parser.add_argument('-b', '--backdating', help='change the date of one file, requires to give a date', type=int, required=False)
    parser.add_argument('-d', '--delete', help='pseudo-randomly delete files, requires to give a number', type=str, required=False)
    parser.add_argument('-v', '--volume', help='Volume to process (i.e C:)', type=str, required=True)
    parser.add_argument('-n', '--stage', help='Stage of the test being processed (i.e 1_creation)', type=str,
                        required=True)
    # parser.add_argument('-b', '--blank', help='File actions are not executed if specified, for blank test', action='store_true')
    # parser.add_argument('-d', '--directory', help='Directory path containing the sleuthkit libraries (icat.exe)', type=str, required=True)
    # parser.add_argument('-o', '--output', help='Destination directory for the $MFT and $bitmap files', required=True)
    args = parser.parse_args()

    curr = os.getcwd()
    os.mkdir(f'{curr}\\data\\{args.stage}')

    logging.basicConfig(filename=f'{curr}\\data\\{args.stage}\\process.txt', format='%(asctime)s - %(name)-12s: %(message)s',
                        datefmt='[%d.%m.%Y %H:%M:%S]', level=logging.INFO)
    logger = logging.getLogger('process')
    logger.info('Starting to process')
    logger.info(f'Current stage : {args.stage}')

    total, used, free = shutil.disk_usage(args.volume)
    logger.info(f'The volume has a capacity of {total} bytes')
    logger.info('Extracting $Bitmap, $Boot and $MFT at blank')
    extract(args.volume, args.stage, 0)
    logger.info("Creating files..")

    n = 1
    while True:
        try:
            create(args.volume + "\\" + str(n), args.size)
            # if args.size:
            #     # fixed file size
            #     create(args.volume + "\\" + str(n), args.size)
            # else:
            #     # random file size : 10 bytes to 100 Mb
            #     random_size = random.randint(100, 100 * 1024 * 1024)
            #     create(args.volume + "\\" + str(n), random_size)

            n += 1
            time.sleep(0.1)

            for i in range(1, total, 100):
                if i == n:
                    logger.info(f"File #{n} was just created ! Extracting the $Bitmap and the $MFT again")
                    extract(args.volume, args.stage, n)

            # if args.backdating:
            #     if n == args.backdating:
            #         backdating(f'{curr}\\data\\{args.stage}\\')


        # Escaping the loop when an OS memory error is catched
        except IOError as e:
            logger.info(f'{str(e)}')
            break

    logger.info('Extracting $Bitmap and $MFT at final stage..!')
    extract(args.volume, args.stage, n)
    # extract_USN_logfile(args.volume, args.stage)

    logger.info('Process finished !')
