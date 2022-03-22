#### Céline Vanini
#### 02.03.2021

import csv
import json
import itertools
from argparse import ArgumentParser
from ressources.ProgressBar import printProgressBar



def parse_bitmap(data):
    res = list(itertools.chain.from_iterable([[1 if byte & 1 << n != 0 else 0 for n in range(8)] for byte in data]))
    return {n: res[n] for n in range(len(res))}

def parse_bitmap_attribute(data):
    res = list(itertools.chain.from_iterable([[1 if byte & 1 << n != 0 else 0 for n in range(8)] for byte in data]))
    return {n: res[n] for n in range(len(res)) if res[n] == 1}

def bitmap_to_json(dict, file):
    with open(file, 'w') as outfile_json:
        json.dump(dict, outfile_json, indent=4)


if __name__ == '__main__':
    parser = ArgumentParser(description='bitmap parser : parse bitmap and return the allocation status per cluster')
    parser.add_argument('-f', '--file', help='$Bitmap file', required=True)
    parser.add_argument('-a', '--attribute', help='$Bitmap attribute of $MFT file', action='store_true')
    parser.add_argument('-c', '--csv', help='save output in a csv file', required=False)
    # parser.add_argument('-e', '--excel', help='save output in a excel sheet', required=False)
    args = parser.parse_args()

    print("Starting to parse the $Bitmap file/$BITMAP attribute")
    with open(args.file, 'rb') as file:
        data = file.read()
        bitmap = parse_bitmap(data)
        bitmap_attribute = parse_bitmap_attribute(data)
        # bitmap_to_json(bitmap, "bitmap.json")
        # if args.number_cluster:
        #     last_key = list(bitmap)[-1]
        #     bitmap = bitmap | {n: 0 for n in range(last_key, args.number_cluster+1)}

    if args.attribute:
        print(f'There are {len(bitmap_attribute)} entries used in the $MFT')

    if args.csv:
        print(f"Starting writting to CSV file..")
        fieldnames = ['Cluster #', 'Status']
        with open(args.csv, 'w', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            n = 1
            for k in bitmap:
                printProgressBar(n, len(bitmap), stage='parsing bytes')
                writer.writerow({'Cluster #': k, 'Status': bitmap[k]})
                n += 1

    # takes some time
    # if args.excel:
    #     if args.excel.endswith(".xlsx"):
    #         df = pd.read_csv(args.csv)
    #         e = df.to_excel(args.excel, header=True, index=False)
    #     else:
    #         raise Exception("The specified destination file must be an .xlsx file")
    #

    print('Process finished !')






