#### Céline Vanini
'''parse the $boot file to verify if the MFT file is '''


import struct
from argparse import ArgumentParser

if __name__ == '__main__':
    parser = ArgumentParser(description='MFT parser : parse MFT entries and return details of each attributes')
    parser.add_argument('-f', '--file', help='MFT file', required=True)