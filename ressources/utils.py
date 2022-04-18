#### Céline Vanini

'''accessory functions for conversion'''
import copy
import csv
import json
from pathlib import Path, WindowsPath
from datetime import datetime, timedelta
from fsparser.ressources.ProgressBar import printProgressBar


def convert_filetime(date_to_convert: int):
    delta = timedelta(microseconds=date_to_convert / 10)
    win_date = datetime(1601, 1, 1, 0, 0, 0)
    timestamp = win_date + delta

    return f'{datetime.strftime(timestamp, "%d.%m.%Y %H:%M:%S +0000")}'


def MFT_to_json(dict, file):
    with open(file, 'w') as outfile_json:
        json.dump(dict, outfile_json, indent=4)


def MFT_to_csv(MFT, file):
    fieldnames = ['ID', 'FILE/BAAD', 'LSN', 'Hard link count', 'Allocation flag', 'Allocation flag (verbose)',
                  'Entry number', 'Base record reference', 'Path', 'SI creation time', 'SI modification time',
                  'SI entry modification time', 'SI last accessed time', 'File type', 'USN', 'FN creation time',
                  'FN modification time', 'FN entry modification time', 'FN last accessed time', 'Parent entry number',
                  'Filename', 'Run list', 'ADS Run list', 'Index flag', 'Index Run list']

    with open(file, 'w', newline='', encoding='utf-8') as outfile_csv:
        writer = csv.DictWriter(outfile_csv, fieldnames=fieldnames)

        writer.writeheader()
        for entry, value in MFT.items():
            if '$STANDARD_INFORMATION' in value:
                si = {'SI creation time': value['$STANDARD_INFORMATION']['Creation time'],
                      'SI modification time': value['$STANDARD_INFORMATION']['Modification time'],
                      'SI entry modification time': value['$STANDARD_INFORMATION']['Entry modification time'],
                      'SI last accessed time': value['$STANDARD_INFORMATION']['Last accessed time'],
                      'File type': value['$STANDARD_INFORMATION']['File type'],
                      'USN': ''}
                if 'Update Sequence Number (USN)' in value['$STANDARD_INFORMATION']:
                    si['USN'] = value['$STANDARD_INFORMATION']['Update Sequence Number (USN)']
            else:
                si = {x: None for x in fieldnames[9:14]}

            if '$FILE_NAME' in value:
                fn = {'FN creation time': value['$FILE_NAME']['Creation time'],
                      'FN modification time': value['$FILE_NAME']['Modification time'],
                      'FN entry modification time': value['$FILE_NAME']['Entry modification time'],
                      'FN last accessed time': value['$FILE_NAME']['Last accessed time'],
                      'Parent entry number': value['$FILE_NAME']['Parent entry number'],
                      'Filename': value['$FILE_NAME']['Filename']}
            else:
                fn = {x: None for x in fieldnames[15:20]}

            if '$DATA' in value:
                if 'Run list' in value['$DATA']:
                    d = {'Run list': value['$DATA']['Run list']}
                else:
                    d = {'Run list': ''}
            else:
                d = {'Run list': ''}

            if '$ADS1' in value:
                if 'Run list' in value['$ADS1']:
                    ads = {'ADS Run list': value['$ADS1']['Run list']}
                else:
                    ads = {'ADS Run list': ''}
            else:
                ads = {'ADS Run list': ''}

            if '$INDEX_ROOT' in value:
                ind = {'Index flag': value['$INDEX_ROOT']['Index flag']}


            if '$INDEX_ALLOCATION' in value:
                if 'Run list' in value['$INDEX_ALLOCATION']:
                    all = {'Index Run list': value['$INDEX_ALLOCATION']['Run list']}
                else:
                    all = {'Index Run list': ''}
            else:
                all = {'Index Run list': ''}

            writer.writerow(dict({'ID': entry,
                                  'FILE/BAAD': value['header']['FILE/BAAD'],
                                  'LSN': value['header']['$LogFile sequence number (LSN)'],
                                  'Hard link count': value['header']['Hard link count'],
                                  'Allocation flag': value['header']['Allocation flag'],
                                  'Allocation flag (verbose)': value['header']['Allocation flag (verbose)'],
                                  'Base record reference': value['header']['Base record reference'],
                                  'Entry number': value['header']['Entry number'],
                                  'Path': value['header']['Path'], **si, **fn, **d, **ads, **ind, **all}))

# This function is used to extract informations on bytes, typically attribute flags
def is_set(x, dict):
    return [dict[n] for n in range(16) if x & 1 << n != 0]

def search(liste, n, element):
    i = 0
    start = 0
    end = n-1

    while i < n:
        middle = (start+end)//2
        if liste[middle] == element:
            return True
        elif liste[middle] < element:
            start = middle+1
        else:
            end = middle-1
        i += 1
    return False

def parse_tree2(MFT):
    temp = copy.deepcopy(MFT)

    temp2 = {k: v for k, v in temp.items() if '$FILE_NAME' in v.keys()}
    temp3 = {k: v for k, v in sorted(temp2.items(), key=lambda x: x[1]['$FILE_NAME']['Parent entry number'])}

    root_directory, root = 5, 'root'
    n = 0
    result = {}
    result[root_directory] = Path(root)
    p_ids = []
    p_ids.append(root_directory)
    length = len(MFT)

    while 1:
        ids = []
        for k, entry in temp3.items():
            printProgressBar(len(result)+1, len(temp3), stage='reconstructing paths [$MFT]')

            current_entry = entry['header']['Entry number']
            parent_entry = entry['$FILE_NAME']['Parent entry number']
            current_filename = entry['$FILE_NAME']['Filename']

            if isinstance(current_filename, list):
                current_filename = current_filename[1]

            if parent_entry in p_ids:
                result[current_entry] = Path(result[parent_entry]) / current_filename
                MFT[k]['header']['Path'] = str(Path(result[parent_entry]) / current_filename)
                ids.append(current_entry)

        p_ids = ids
        if len(result) == len(temp3):
            break

    return MFT

# Build the path of each entries file/dir recursively
# Can be then used to sort based on Path (ex. keep only C:\Users\)
def parse_tree(MFT):
    root_directory, root = 5, 'root'
    n = 0
    result = {}
    result[root_directory] = Path(root)
    p_ids, ids = [], []
    p_ids.append(root_directory)
    lonely_childs = list(range(0,len(MFT)+1))
    length = len(MFT)

    n = 0

    for k, entry in MFT.items():
        printProgressBar(len(result), length, stage='reconstructing paths [$MFT]')
        current_entry = entry['header']['Entry number']
        match n:
            case 0:
                if '$FILE_NAME' in entry:
                    parent_entry = entry['$FILE_NAME']['Parent entry number']
                    current_filename = entry['$FILE_NAME']['Filename']

                    if isinstance(current_filename, list):
                        current_filename = current_filename[1]

                    if parent_entry in p_ids:
                        result[current_entry] = Path(result[parent_entry]) / current_filename
                        entry['header']['Path'] = str(Path(result[parent_entry])/current_filename)
                        ids.append(current_entry)
                        lonely_childs.remove(current_entry)

                else:
                    result[current_entry] = ''

    p_ids = ids
    n = 1

    for lonely_child, parent in lonely_childs.items():
        if parent[0] in p_ids:
            result[lonely_child] = Path(result[parent[0]]) / parent[1]
            MFT[lonely_child]['header']['Path'] = str(Path(result[parent[0]]) / parent[1])

    print(len(result))
    print(len(lonely_childs))


    return MFT

if __name__ == '__main__':
    pass
