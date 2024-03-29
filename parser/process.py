#### Céline Vanini
#### Main module processing the experiments from creating files to extract system files of interest

# The script must be executed as administrator in a Powershell console !
# Do not run it on your volume ! It would be overwritten :)
# python .\process.py -v "C:" -n "1" -s 10

import os
import time
from MFT import *
from bitmap import *
from boot import *
import random
import shutil
import logging
import subprocess
from ressources.MFT_utils import *
from datetime import datetime, timedelta
from argparse import ArgumentParser

logger = logging.getLogger('process')
curr = os.getcwd()


def extract_from_volume(volume, stage, n):
    logger.info('Extracting $Bitmap, $Boot and $MFT')

    curr = os.getcwd()
    path = f'{curr}\\data\\{stage}\\{str(n)}'
    if os.path.isdir(path):
        path = f'{curr}\\data\\{stage}\\{str(n)}_'
    os.mkdir(path)

    # Extracting and parsing the $boot to obtain volume information
    if n == 0:
        subprocess.run(['icat.exe', f'\\\\.\\{volume}', '7', '>', f"{path}\\$Boot"], cwd=f'{curr}\\sleuthkit\\bin\\',
                       shell=True)
        parse_boot(f'{path}\\$Boot')
    # Parsing the $BITMAP attribute in the entry 0 of the $MFT (used for the MFT file itself..)
    # It contains the number of entries that are used in the $MFT, so can be compared with the result of the
    # MTF.py script, to be sure it parsed all entries.
    subprocess.run(['icat.exe', f'\\\\.\\{volume}', '0-176', '>', f"{path}\\MFT_bitmap"],
                   cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)
    # command to copy the $Bitmap of the specified volume (entry 6)
    subprocess.run(['icat.exe', f'\\\\.\\{volume}', '6', '>', f"{path}\\$Bitmap"], cwd=f'{curr}\\sleuthkit\\bin\\',
                   shell=True)
    # command to copy the $MFT of the specified volume (entry 0)
    subprocess.run(['icat.exe', f'\\\\.\\{volume}', '0', '>', f"{path}\\$MFT"], cwd=f'{curr}\\sleuthkit\\bin\\',
                   shell=True)

    return path


def parse_all(path):
    # bitmap_dict = bitmap.parse_bitmap(f'{path}\\$Bitmap')
    # bitmap.to_csv(path, bitmap_dict)
    ##len = parse_bitmap_MFT(f'{path}\\$MFT')
    MFT_dict = parse_MFT(f'{path}\\$MFT')

    #logger.info(f'There are {len} used entries in the MFT bitmap attribute')
    #if len == len(MFT_dict):
    #    logger.info(f'All entries were extracted during the process')
    #else:
    #    logger.info(f'Check the script, errors might have occured')
    MFT_to_csv(f"{path}", MFT_dict)


def activate_USN(volume):
    subprocess.run(['fsutil', 'usn', 'createJournal', volume], shell=True)


def extract_USN_logfile(volume, stage):
    # pas aussi simple que ça pour l'USN, pas toujours le même numéro d'entrée:
    logger.info(f"Extracting the $UsnJrnl")
    subprocess.run(['fls.exe', f'\\\\.\\{volume}', '11'],
                   cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)
    attribute = input("Please write the attribute number containing the $J: ")
    subprocess.run(['icat.exe', f'\\\\.\\{volume}', attribute, '>', f"{curr}\\data\\{stage}\\$J"],
                   cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)
    logger.info(f"Extracting the $LogFile")
    subprocess.run(['icat.exe', f'\\\\.\\{volume}', '2', '>', f"{curr}\\data\\{stage}\\$LogFile"],
                   cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)

def parse_usn(stage):
    subprocess.run(['python', 'usn.py', '--verbose', '-f', f'{curr}\\data\\{stage}\\$J', '-o', f'{curr}\\data\\{stage}\\usn.txt'], cwd=f'{curr}\\usn_parser\\', shell=True)


# create files of the specified size, in bytes.
def create(path, size):
    with open(str(path) + '.txt', 'wb') as file:
        # megabytes : file.write(b'0' * size * 1024 * 1024)
        file.write(b'0' * size)

        # flushing internal buffers and force writing to disk
        file.flush()
        os.fsync(file.fileno())


def delete(path, k):
    subprocess.run(["del", f"{path}\\{str(k-5)}.txt"], shell=True)
    logger.info(f"Deleted {str(k-5)}.txt at {datetime.now()}")
    # k = int(k)
    # try:
    #     rand = random.randint(1, k-1)
    #     if os.path.exists(f"{path}\\{rand}.txt"):
    #         os.remove(f"{path}\\{rand}.txt")
    #         logger.info(f"Deleted {rand}.txt at {datetime.now()}")
    # except Exception:
    #     pass

def formatting():
    subprocess.run("diskpart", shell=True)
    # subprocess.run("list disk", shell=True)
    # n = input("Please write the disk number : ")
    # subprocess.run("select", "disk", f"{n}", shell=True)
    # subprocess.run("clean", shell=True)
    # subprocess.run("format", "fs=ntfs", shell=True)
    # subprocess.run("assign", shell=True)


# manipulating timestamps with Powershell command lines
def backdating(path):
    file = os.listdir(path)[-1]
    d = datetime.now(None) - timedelta(minutes=15)
    d = datetime.strftime(d, "%d.%m.%Y %H:%M:%S")
    logger.info(f"Backdating file {file} to {d}")

    if file.endswith('.txt'):
        subprocess.run([f"$(Get-Item {path}\\{file}).creationtime=$(Get-Date \"{d}\")"], shell=True)
        subprocess.run([f"$(Get-Item {path}\\{file}).lastaccesstime=$(Get-Date \"{d}\")"], shell=True)
        subprocess.run([f"$(Get-Item {path}\\{file}).lastwritetime=$(Get-Date \"{d}\")"], shell=True)

#
# def algorithm(volume, path):
#     subprocess.run(['icat.exe', f'\\\\.\\{volume}', '6', '>', f"{path}\\$Bitmap"], cwd=f'{curr}\\sleuthkit\\bin\\',
#                    shell=True)
#     b = parse_bitmap(f"{path}\\$Bitmap")
#     test_algorithm(b)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-s', '--size',
                        help='Size of the file to be created (in bytes), if not specified, creates files of random size',
                        type=int, required=False)
    parser.add_argument('-v', '--volume', help='Volume to process (i.e C:)', type=str, required=True)
    parser.add_argument('-n', '--stage', help='Stage of the test being processed (i.e 1_creation)', type=str,
                        required=True)

    # parser.add_argument('-b', '--backdating', help='change the date of one file, requires to give a date', type=int, required=False)
    # parser.add_argument('-d', '--delete', help='pseudo-randomly delete files, requires to give a number', type=str, required=False)
    # parser.add_argument('-o', '--output', help='Destination directory for the $MFT and $bitmap files', required=True)
    args = parser.parse_args()

    curr = os.getcwd()
    os.mkdir(f'{curr}\\data\\{args.stage}')

    logging.basicConfig(
        handlers=[logging.FileHandler(f'{curr}\\data\\{args.stage}\\process.txt'), logging.StreamHandler()],
        format='%(asctime)s - %(name)-12s: %(message)s',
        datefmt='[%d.%m.%Y %H:%M:%S]', level=logging.INFO)

    logger.info('Starting to process')
    logger.info(f'Current stage : {args.stage}')

    total, used, free = shutil.disk_usage(args.volume)
    logger.info(f'The volume has a capacity of {total} bytes')
    # activate_USN(args.volume)
    # extract_from_volume(args.volume, args.stage, 0)
    # algorithm(args.volume, f'{curr}\\data\\{args.stage}')

    # logger.info("Creating files..")

    n = 1
    # p = extract_from_volume(args.volume, args.stage, 0)
    # parse_all(p)
    #
    # while True:
    #     # To have the disk not full
    #     # while n < 800:
    #     try:
    #         # creating files directly from the command line :
    #         # subprocess.run(["fsutil", "file", "createnew", f"{args.volume}\\{str(n)}.txt", f"{args.size}"])
    #         if args.size:
    #             # fixed file size
    #             create(f'{args.volume}\\{str(n)}', args.size)
    #         else:
    #             # random file size
    #             random_size = random.randint(100, 1024 * 1024 * 20)
    #             create(f'{args.volume}\\{str(n)}', random_size)
    #             # to create files with random names (test if there is a difference with because of the B+-Tree)
    #             # random_string = ''.join(random.choice(string.ascii_lowercase) for i in range(1,6))
    #             # create(args.volume + '\\' + str(random_string), random_size)
    #
    #         # if n == 150:
    #         #     delete(args.volume, n)
    #
    #         # for i in range(100, total, 100):
    #         #     if i == n:
    #         #         logger.info("Deleting a file")
    #         #         delete(args.volume, n)
    #
    #         n += 1
    #         time.sleep(random.uniform(0.4, 0.7))
    #         # time.sleep(2)
    #         # to extract the system files at some stage of the process
    #         # for i in range(1, total, 100):
    #         #     if i == n:
    #         #         logger.info(f"File #{n} was just created!")
    #         #         p = extract_from_volume(args.volume, args.stage, n)
    #         #         parse_all(p)
    #
    #         # for i in range(1, total, 100):
    #         #     if i == n:
    #         #         logger.info(f"File #{n} was just created !")
    #         #         p = extract(args.volume, args.stage, n)
    #         #         parse_all(p)
    #         # logger.info(f'File {n} created size: {random_size // 4096}')
    #
    #
    #         # if args.backdating:
    #         #    if n == args.backdating:
    #         #        backdating(f'{args.volume}')
    #
    #         # to test the algorithm
    #         # logger.info(f'File {n} created size : {random_size/4096}')
    #         # for j in range(50, total, 100):
    #         #     if j == n:
    #         #         delete(args.volume, n)
    #         #         logger.info(f"File {n} was deleted")
    #
    #         # algorithm(args.volume, f'{curr}\\data\\{args.stage}')
    #
    #
    #     # Escaping the loop when an OS memory error is catched
    #     except IOError as e:
    #         logger.info(f'{str(e)}')
    #         break

    logger.info('Extracting $Bitmap and $MFT at final stage..!')
    p = extract_from_volume(args.volume, args.stage, n)
    parse_all(p)

    # bloup = input("Please format the disk")

    # extract_USN_logfile(args.volume, args.stage)
    # parse_usn(args.stage)
    # formatting()
    # p = extract_from_volume(args.volume, args.stage, n+1)
    # parse_all(p)
    # extract_USN_logfile(args.volume, args.stage)


    logger.info('Process finished !')
