#### Céline Vanini
#### 02.03.2022

#Exemple commande :  python .\bitmap.py -f "C:\Users\celin\UNIVERSITE\MA2S2\TdM\Results\_22042022_1\0\`$Bitmap" -o ".\outputs\"

import csv, os
import logging
import itertools
from tqdm import tqdm
import more_itertools as mit
from argparse import ArgumentParser

bitmap_logger = logging.getLogger('bitmap')


# general method to parse the $Bitmap, check for each position if 1 or 0
def extracting_status(data):
    res = list(itertools.chain.from_iterable([[1 if byte & 1 << n != 0 else 0 for n in range(8)] for byte in data]))
    return {n: res[n] for n in range(len(res))}

# f'{path}\\{str(k)}\\$Bitmap'
def parse_bitmap(path):
    bitmap_logger.info("Starting to parse the $Bitmap file")

    with open(path, 'rb') as file:
        data = file.read()
        bitmap = extracting_status(data)

    bitmap_logger.info("Process finished !")

    return bitmap


# writes the bitmap content into CSV with two columns (Cluster number/Status : allocated or not)
def bitmap_to_csv(dir, bitmap):
    bitmap_logger.info(f"Starting writting to CSV file..")
    fieldnames = ['Cluster #', 'Status']
    with open(f'{dir}\\Bitmap.csv', 'w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        n = 1
        for k in tqdm(bitmap, desc='[Bitmap]'):
            writer.writerow({'Cluster #': k, 'Status': bitmap[k]})
            n += 1

    bitmap_logger.info('CSV file of the $Bitmap is written !')


# Used to test the best fit algorithm on a volume
def test_algorithm(bitmap):
    bitmap_logger.info(f"Extracting information on available free spaces")
    # do the inventory of free spaces by considering sequences of zeros
    free_spaces = [int(k) for k, v in tqdm(bitmap.items(), desc='[Looking for free spaces]') if v == 0]
    bitmap_logger.info(f"Creating ranges of free space")
    # creates lists of intervals of free spaces, sorted by length
    list_ranges = sorted([list(group) for group in mit.consecutive_groups(free_spaces)], key=lambda x: len(x))
    ranges = [f"[{x[0]}{'-' + str(x[-1]) if len(x) > 1 else ''}]" for x in list_ranges]
    bitmap_logger.info(f'List of free spaces sorted by ascending size :\n{ranges}')



if __name__ == '__main__':
    parser = ArgumentParser(description='bitmap parser : parse bitmap and return the allocation status per cluster')
    parser.add_argument('-f', '--file', help='$Bitmap file', required=True)
    parser.add_argument('-o', '--output', help='directory output to write the csv file + logging process', required=True)

    args = parser.parse_args()

    if not os.path.isdir(args.output):
        os.mkdir(args.output)


    logging.basicConfig(format='%(asctime)s - %(name)-12s: %(message)s',
                        datefmt='[%d.%m.%Y %H:%M:%S]', level=logging.INFO,
                        handlers=[logging.FileHandler(f'{args.output}\\bitmap.txt'), logging.StreamHandler()])

    bitmap = parse_bitmap(args.file)
    bitmap_to_csv(args.output, bitmap)
    # test_algorithm(bitmap)


