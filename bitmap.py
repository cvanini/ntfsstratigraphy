#### Céline Vanini
#### 02.03.2021

import csv
import json
import logging
import itertools
from argparse import ArgumentParser
from ressources.ProgressBar import printProgressBar

bitmap_logger = logging.getLogger('bitmap')


# general method to parse the $Bitmap, check for each position if 1 or 0
def parse_bitmap(data):
    res = list(itertools.chain.from_iterable([[1 if byte & 1 << n != 0 else 0 for n in range(8)] for byte in data]))
    return {n: res[n] for n in range(len(res))}


# method for parsing the bitmap attribute in the entry 0 of the $MFT, indicating the entries allocated
# used to check if the MFT.py does its job correctly ! (doesn't forget any entry)
def parse_bitmap_attribute(data):
    res = list(itertools.chain.from_iterable([[1 if byte & 1 << n != 0 else 0 for n in range(8)] for byte in data]))
    return {n: res[n] for n in range(len(res)) if res[n] == 1}


# def bitmap_to_json(dict, file):
#     with open(file, 'w') as outfile_json:
#         json.dump(dict, outfile_json, indent=4)


def main(path, k):
    with open(path + '\\$Bitmap', 'rb') as file:
        data = file.read()
        bitmap = parse_bitmap(data)
        to_csv(path + f'_{str(k)}.csv', bitmap)


def main_attribute(path):
    with open(path + '\\MFT_bitmap', 'rb') as file:
        data = file.read()
        bitmap_attribute = parse_bitmap_attribute(data)

    bitmap_logger.info(f'There are {len(bitmap_attribute)} entries used in the $MFT')

def to_csv(path, bitmap):
    bitmap_logger.info(f"Starting writting to CSV file..")
    fieldnames = ['Cluster #', 'Status']
    with open(path, 'w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        n = 1
        for k in bitmap:
            printProgressBar(n, len(bitmap), stage='parsing bytes [$bitmap]')
            writer.writerow({'Cluster #': k, 'Status': bitmap[k]})
            n += 1

    bitmap_logger.info('CSV file of the $Bitmap is written !')

def log(path, k):
    bitmap_logger.info("Starting to parse the $Bitmap file/$BITMAP attribute")
    main_attribute(path)
    main(path, k)
    bitmap_logger.info("Process finished !")




if __name__ == '__main__':
    parser = ArgumentParser(description='bitmap parser : parse bitmap and return the allocation status per cluster')
    parser.add_argument('-f', '--file', help='$Bitmap file', required=True)
    parser.add_argument('-a', '--attribute', help='$Bitmap attribute of $MFT file', action='store_true')
    parser.add_argument('-c', '--csv', help='save output in a csv file', required=False)
    # parser.add_argument('-e', '--excel', help='save output in a excel sheet', required=False)
    args = parser.parse_args()

    # logging.info("Starting to parse the $Bitmap file/$BITMAP attribute")
    # with open(args.file, 'rb') as file:
    #     data = file.read()
    #     bitmap = parse_bitmap(data)
    #     bitmap_attribute = parse_bitmap_attribute(data)

    # if args.attribute:
    #     logging.info(f'There are {len(bitmap_attribute)} entries used in the $MFT')

    # if args.csv:
    #     logging.info(f"Starting writting to CSV file..")
    #     fieldnames = ['Cluster #', 'Status']
    #     with open(args.csv, 'w', newline='') as csv_file:
    #         writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    #         writer.writeheader()
    #
    #         n = 1
    #         for k in bitmap:
    #             printProgressBar(n, len(bitmap), stage='parsing bytes')
    #             writer.writerow({'Cluster #': k, 'Status': bitmap[k]})
    #             n += 1
    #
    #     logging.info('CSV file of the $Bitmap is written !')
