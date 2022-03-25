import os
import shutil
import subprocess
from argparse import ArgumentParser
from pathlib import Path, PureWindowsPath
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

    print(os.listdir()[0])
    print(datetime.now(None))
    s = "25.03.2022 14:30:00"
    d = datetime.strptime(s, "%d.%m.%Y %H:%M:%S")
    print(d)
    d2 = datetime.now(None) - timedelta(minutes=15)
    print(datetime.strftime(d2, "%d.%m.%Y %H:%M:%S"))


