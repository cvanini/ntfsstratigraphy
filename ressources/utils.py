#### Céline Vanini

'''accessory functions for conversion'''
import copy
import csv
import json
import struct
from pathlib import Path, WindowsPath
from datetime import datetime, timedelta
from ressources.ProgressBar import printProgressBar


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

            if 'ADS1' in value:
                if 'Run list' in value['ADS1']:
                    ads = {'ADS Run list': value['ADS1']['Run list']}
                else:
                    ads = {'ADS Run list': ''}
            else:
                ads = {'ADS Run list': ''}

            if '$INDEX_ROOT' in value:
                ind = {'Index flag': value['$INDEX_ROOT']['Index flag']}
            else:
                ind = {'Index flag': ''}


            if '$INDEX_ALLOCATION' in value:
                if 'Data run' in value['$INDEX_ALLOCATION']:
                    all = {'Index Run list': value['$INDEX_ALLOCATION']['Data run']}
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

def unpack6(x):
    x1, x2, x3 = struct.unpack('<HHH', x)
    return (x1 + (x2 << 16) + (x3 << 32))

# Build the path of each entries file/dir recursively
# Can be then used to sort based on Path (ex. keep only C:\Users\)
# TODO : gérer les séquences ?
def parse_tree(MFT):

    temp_MFT = copy.deepcopy(MFT)
    length = len(MFT)

    # Paths are stored on this dictionary :
    result = {}
    result[5] = Path('root')
    # Parents that already have their path found are appended to this list :
    p_ids = [5]

    n = 0
    while 1:
        for k, entry in temp_MFT.items():
            printProgressBar(len(result)+1, length, stage='reconstructing paths [$MFT]')
            # As there can be multiple filenames (cf. hard links):
            # p = []
            if '$FILE_NAME' in entry:
                for m in entry:
                    if m.startswith('$FILE_NAME'):
                        parent_entry = entry[m]['Parent entry number']
                        current_filename = entry[m]['Filename']

                        if parent_entry in p_ids:
                            result[k] = Path(result[parent_entry]) / current_filename
                            # p.append(str(Path(result[parent_entry]) / current_filename))
                            MFT[k]['header']['Path'] = str(Path(result[parent_entry]) / current_filename)
                            p_ids.append(k)
                        else:
                            # print(f'passing {current_entry}, {current_filename}, {parent_entry}')
                            pass
            # some entries do not have a $FILE_NAME
            else:
                result[k] = ''
                MFT[k]['header']['Path'] = ''
                p_ids.append(k)

        # creating a new instance of the temporary MFT dictionary, without the entries that have their path already
        # reconstructed and put into result (to avoid redundancy)
        if len(result.keys()) == length:
            break
        # elif n == 10:
        #     lonely_childs = [(k, v['$FILE_NAME']['Parent entry number'], v['$FILE_NAME']['Filename']) for k, v in temp_MFT.items() if '$FILE_NAME' in v]
        #     print(lonely_childs)
        #     break
        else:
            temp_MFT = {k: v for k, v in temp_MFT.items() if k not in p_ids}

        n += 1

    return MFT


if __name__ == '__main__':
    pass
