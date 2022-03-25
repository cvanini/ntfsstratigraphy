import os
import shutil
import subprocess
from argparse import ArgumentParser
from pathlib import Path, PureWindowsPath
import logging
import boot


def create(path, size, n):

    path2 = path + '\\' + str(n)
    with open(path2 + str(n) + '.txt', 'wb') as file:
        file.write(b'0' * size)

        # flushing internal buffers and force write to disk
        file.flush()
        os.fsync(file.fileno())


if __name__ == '__main__':
    logging.basicConfig(filename='process.txt', datefmt='%d.%m.%Y %H:%M:%S', format='[%(asctime)s] %(message)s', level=logging.INFO)
    logger = logging.getLogger('main')
    logger.info('Starting to process')
    file = os.getcwd() + "\\data\\CT\\$boot"
    boot.parse_boot(file)


