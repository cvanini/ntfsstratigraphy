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

    # command to extract the $MFT and $bitmap from the running drivee
    p = subprocess.run(['icat.exe', '\\\\.\\C:', '0', '>',
                        'C:\\Users\\celin\\UNIVERSITÉ\\MA2S2\\Travail de Master\\Forensic-Tools\\data\\1_creation\\0\\$MFT'],
                       cwd='.\\sleuthkit\\bin\\', shell=True)
    p = subprocess.run(['icat.exe', '\\\\.\\C:', '6', '>',
                        'C:\\Users\\celin\\UNIVERSITÉ\\MA2S2\\Travail de Master\\Forensic-Tools\\data\\1_creation\\0\\$bitmap'],
                       cwd='.\\sleuthkit\\bin\\', shell=True)

    n = 1
    while True:
        try:
            create(args.destination + "\\" + str(n), args.size)
            n += 1
            time.sleep(2)

            for i in range(1,10000,10):
                if i == n:
                    os.mkdir(f'.\\data\\{str(i)}')
                    p = subprocess.run(['icat.exe', '\\\\.\\C:', '0', '>',
                                        f'C:\\Users\\celin\\UNIVERSITÉ\\MA2S2\\Travail de Master\\Forensic-Tools\\data\\1_creation\\{str(i)}\\$MFT'],
                                        cwd='.\\sleuthkit\\bin\\', shell=True)
                    q = subprocess.run(['icat.exe', '\\\\.\\C:', '6', '>',
                                        f'C:\\Users\\celin\\UNIVERSITÉ\\MA2S2\\Travail de Master\\Forensic-Tools\\data\\1_creation\\{str(i)}\\$bitmap'],
                                        cwd='.\\sleuthkit\\bin\\', shell=True)
        except IOError:
            break


    # command to extract the $MFT and $bitmap from the running drivee
    p = subprocess.run(['icat.exe', '\\\\.\\C:', '0', '>',
                        'C:\\Users\\celin\\UNIVERSITÉ\\MA2S2\\Travail de Master\\Forensic-Tools\\data\\$MFT'],
                       cwd='.\\sleuthkit\\bin\\', shell=True)
    p = subprocess.run(['icat.exe', '\\\\.\\C:', '6', '>',
                        'C:\\Users\\celin\\UNIVERSITÉ\\MA2S2\\Travail de Master\\Forensic-Tools\\data\\$bitmap'],
                       cwd='.\\sleuthkit\\bin\\', shell=True)

