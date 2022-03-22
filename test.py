import os
import shutil
import subprocess
from argparse import ArgumentParser
from pathlib import Path, PureWindowsPath

def create(path, size, n):

    os.mkdir(path + '\\' + str(n))
    path2 = path + '\\' + str(n)
    with open(path2 + str(n) + '.txt', 'wb') as file:
        file.write(b'0' * size * 1024 * 1024)

        # flushing internal buffers and force write to disk
        file.flush()
        os.fsync(file.fileno())


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-d', '--destination', help='Destination disk', required=True)
    args = parser.parse_args()
    #
    path = str(PureWindowsPath(args.destination))
    # print(str(path))
    os.mkdir(f'.\\data\\{str(1)}')

    #p = subprocess.run(['exiftool.exe', '-h'], cwd=str(path), shell=True)
    total, used, free = shutil.disk_usage("C:")
    print((total//2**30), used, free)
