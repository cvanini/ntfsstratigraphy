import csv, json
import pandas as pd
import itertools
from argparse import ArgumentParser


# TODO : padding jusqu'au nombre de cluster dans le disque ?
# Lent quand il y a beaucoup de données (ex. avec le 512 de CT)
def parse_bitmap(data):
    res = list(itertools.chain.from_iterable([[1 if byte & 1 << n != 0 else 0 for n in range(8)] for byte in data]))
    return {n: res[n] for n in range(len(res))}

def bitmap_to_json(dict, file):
    with open(file, 'w') as outfile_json:
        json.dump(dict, outfile_json, indent=4)


if __name__ == '__main__':
    parser = ArgumentParser(description='bitmap parser : parse bitmap and return the allocation status per cluster')
    parser.add_argument('-f', '--file', help='$Bitmap file', required=True)
    # parser.add_argument('-n', '--number_cluster', help='number of clusters in the volume, if specified, add padding at\
    #                     the end of the bitmap to have the complete volume allocation', required=False, type=int)
    parser.add_argument('-c', '--csv', help='save output in a csv file', required=False)
    parser.add_argument('-e', '--excel', help='save output in a excel sheet', required=False)
    args = parser.parse_args()

    with open(args.file, 'rb') as file:
        print("Starting to parse the $Bitmap file")
        data = file.read()
        bitmap = parse_bitmap(data)
        # bitmap_to_json(bitmap, "bitmap.json")
        # if args.number_cluster:
        #     last_key = list(bitmap)[-1]
        #     bitmap = bitmap | {n: 0 for n in range(last_key, args.number_cluster+1)}

    if args.csv:
        print(f"Starting writting to CSV file..")
        fieldnames = ['Cluster #', 'Status']
        with open(args.csv, 'w', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            for k in bitmap:
                writer.writerow({'Cluster #': k, 'Status': bitmap[k]})

    # takes some time
    if args.excel:
        if args.excel.endswith(".xlsx"):
            df = pd.read_csv(args.csv)
            e = df.to_excel(args.excel, header=True, index=False)
        else:
            raise Exception("The specified destination file must be an .xlsx file")
        # print('Writting into an Excel sheet..')
        # df = pd.DataFrame(data=bitmap, index=[0]).T
        # df.to_excel(args.excel, index_label='Cluster #', header=['Status'])

    print('Process finished !')






