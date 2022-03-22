#### Céline Vanini
#### Main module processing the experiment from creating files to extract system files of interest

# The script must be executed as administrator !
# python .\process.py -v "C:" -s "1_creation"

import os
import time
import shutil
import subprocess
from argparse import ArgumentParser


def extract(volume, stage, n):
    curr = os.getcwd()
    os.mkdir(os.getcwd() + f'\\data\\{stage}\\{str(n)}')
    # $MFT
    p = subprocess.run(['icat.exe', f'\\\\.\\{volume}', '0', '>', f"{curr}\\data\\{stage}\\{str(n)}\\$MFT"],
                       cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)
    # $Bitmap
    p = subprocess.run(['icat.exe', f'\\\\.\\{volume}', '6', '>', f"{curr}\\data\\{stage}\\{str(n)}\\$Bitmap"],
                       cwd=f'{curr}\\sleuthkit\\bin\\', shell=True)

def create(path, size):
    with open(str(path) + '.txt', 'wb') as file:
        file.write(b'0' * size * 1024 * 1024)

        # flushing internal buffers and force write to disk
        file.flush()
        os.fsync(file.fileno())


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-s', '--size', help='Size of the file to be created (in megabytes)', type=int, required=True)
    parser.add_argument('-v', '--volume', help='Volume to process (i.e C:)', type=str, required=True)
    parser.add_argument('-s', '--stage', help='Stage of the test being processed (i.e 1_creation)', type=str, required=True)
    # parser.add_argument('-b', '--blank', help='File actions are not executed if specified, for blank test', action='store_true')
    # parser.add_argument('-d', '--directory', help='Directory path containing the sleuthkit libraries (icat.exe)', type=str, required=True)
    # parser.add_argument('-o', '--output', help='Destination directory for the $MFT and $bitmap files', required=True)
    args = parser.parse_args()

    print('Starting to process..')
    total, used, free = shutil.disk_usage("C:")
    print(f'The volume has a capacity of {total} bytes')

    print('Extracting $Bitmap and $MFT at blank')
    os.mkdir(os.getcwd()+f'\\data\\{args.stage}')
    extract(args.volume, args.stage, 0)

    print(f'Creating files of {args.size} megabytes')
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
                    extract(args.volume, args.stage, n)

        except IOError:
            break

    print('Extracting $Bitmap and $MFT at final stage')
    extract(args.volume, args.stage, n)


