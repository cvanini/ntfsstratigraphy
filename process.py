import os
import time
import subprocess
from argparse import ArgumentParser


def create(path, size):
    with open(str(path) + '.txt', 'wb') as file:
        file.write(b'0' * size * 1024 * 1024)

        # flushing internal buffers and force write to disk
        file.flush()
        os.fsync(file.fileno())


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-s', '--size', help='Size of the file to be created (in megabytes)', type=int, required=True)
    parser.add_argument('-d', '--destination', help='Destination disk', required=True)
    args = parser.parse_args()

    n = 0
    while True:
        try:
            create(args.destination + "\\" + str(n), args.size)
            n += 1
            time.sleep(2)
        except IOError:
            break

    p = subprocess.call(["cd .\\sleutkit\\bin && ifind.exe -h"], shell=True)