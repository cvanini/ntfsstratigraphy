#### Céline Vanini
#### Main module processing the experiment from creating files to extract system files of interest

# The script must be executed as administrator !
# Do not run it on your volume ! It would be overwritten :)
# python .\process.py -v "C:" -n "1" -s 10

import os
import time
import shutil
import subprocess
from argparse import ArgumentParser


def extract(volume, stage, n):
    curr = os.getcwd()
    os.mkdir(os.getcwd() + f'\\data\\{stage}\\{str(n)}')

    # Parsing the $BITMAP attribute in the entry 0 of the $MFT (used for the MFT file itself..)
    # It contains the number of entries that are used in the $MFT, so can be compared with the result of the
    # MTF.py script, to be sure it parsed all entries.
    subprocess.run(['icat.exe', f'\\\\.\\{volume}', '0-176', '>', f"{curr}\\data\\{stage}\\{str(n)}\\MFT_bitmap"],
                   cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)
    subprocess.run(['python', 'bitmap.py', '-f', f"{curr}\\data\\{stage}\\{str(n)}\\MFT_bitmap", '-a'],
                   cwd=f'{curr}\\', shell=True)

    # command to copy the $MFT of the specified volume (entry 0) and parse it with the MFT.py python script
    subprocess.run(['icat.exe', f'\\\\.\\{volume}', '0', '>', f"{curr}\\data\\{stage}\\{str(n)}\\$MFT"],
                       cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)
    subprocess.run(['python', 'MFT.py', '-f', f"{curr}\\data\\{stage}\\{str(n)}\\$MFT", '-c', f"{curr}\\outputs\\{stage}\\MFT_{str(n)}.csv"],
                      cwd=f'{curr}\\', shell=True)

    # command to copy the $Bitmap of the specified volume (entry 6) and parse it with the bitmap.py python script
    subprocess.run(['icat.exe', f'\\\\.\\{volume}', '6', '>', f"{curr}\\data\\{stage}\\{str(n)}\\$Bitmap"],
                       cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)
    subprocess.run(['python', 'bitmap.py', '-f', f"{curr}\\data\\{stage}\\{str(n)}\\$Bitmap", '-c', f"{curr}\\outputs\\{stage}\\Bitmap_{str(n)}.csv"],
                   cwd=f'{curr}\\', shell=True)

# create files of the specified size, in megabytes.
def create(path, size):
    with open(str(path) + '.txt', 'wb') as file:
        file.write(b'0' * size * 1024 * 1024)

        # flushing internal buffers and force write to disk
        file.flush()
        os.fsync(file.fileno())

def randomly_create(path):
    pass

def delete(path):
    pass


if __name__ == '__main__':
    parser = ArgumentParser()
    # parser.add_argument('-s', '--size', help='Size of the file to be created (in megabytes)', type=int, required=True)
    parser.add_argument('-v', '--volume', help='Volume to process (i.e C:)', type=str, required=True)
    parser.add_argument('-n', '--stage', help='Stage of the test being processed (i.e 1_creation)', type=str, required=True)
    # parser.add_argument('-b', '--blank', help='File actions are not executed if specified, for blank test', action='store_true')
    # parser.add_argument('-d', '--directory', help='Directory path containing the sleuthkit libraries (icat.exe)', type=str, required=True)
    # parser.add_argument('-o', '--output', help='Destination directory for the $MFT and $bitmap files', required=True)
    args = parser.parse_args()

    print('Starting to process..')
    total, used, free = shutil.disk_usage("C:")
    print(f'The volume has a capacity of {total} bytes')

    print('Extracting $Bitmap and $MFT at blank')
    os.mkdir(os.getcwd()+f'\\data\\{args.stage}')
    os.mkdir(os.getcwd()+f'\\outputs\\{args.stage}')

    extract(args.volume, args.stage, 0)

    print("Creating files..")
    file_size = args.size * 1024 * 1024
    max = total//file_size

    n = 1
    while max > n:
        try:
            create(args.volume + "\\" + str(n), args.size)
            n += 1
            time.sleep(0, 2)

            for i in range(1, 10000, 100):
                if i == n:
                    print(f"File #{n} was just created !")
                    extract(args.volume, args.stage, n)

        except IOError:
            break

    print('Extracting $Bitmap and $MFT at final stage')
    extract(args.volume, args.stage, n)


