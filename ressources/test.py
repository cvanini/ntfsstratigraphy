import os
import struct

import utils
import fsparser


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

    with open('..\data\CT\$MFT', 'rb') as f:
        data = f.read(1024)

    print(data[0:4])
    print(data[4:8])
    b = b'\x00\x1F\x00\xD1'
    #print(utils.unpack6(b)[0])
    x, y, z = struct.unpack('<HHH', data[4:10])
    print(x, y, z)
    print(x + (y << 16) + (z <<32))

