import os
import shutil
import subprocess
from pathlib import PureWindowsPath
from argparse import ArgumentParser
from pathlib import Path, WindowsPath
import logging
import boot
from datetime import datetime, timedelta


def create(path, size):

    with open(path + 'test2.txt', 'wb') as file:
        file.write(b'0' * size)

        # flushing internal buffers and force write to disk
        file.flush()
        os.fsync(file.fileno())

def delete(path, filename):
    if os.path.exists(path + "\\" + filename):
        os.remove(path + "\\" + filename)


if __name__ == '__main__':

    variable = '$I30'
    match variable:
        # Index of filenames
        case '$I30':
            print('Directory')
        case '$SDH':
            print('Security descriptors')
        case '$SII':
            print('bloup')