import os
import struct

import MFT_utils


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

    d = {1: {'header': {'Resident': 1, 'bloup': 2}}, 2: {'header': {'Resident': 0}}}
    l = {k : v for k, v in d.items() if v['header']['bloup'] == 2}
