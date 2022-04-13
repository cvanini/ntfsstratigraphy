#### Céline Vanini

'''accessory functions for conversion'''

import csv
import json
from pathlib import Path, WindowsPath
from datetime import datetime, timedelta


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
                  'Entry number', 'Base record reference', 'SI creation time', 'SI modification time',
                  'SI entry modification time',
                  'SI last accessed time', 'File type', 'USN', 'FN creation time', 'FN modification time',
                  'FN entry modification time', 'FN last accessed time', 'Parent entry number', 'Filename', 'Run list']

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
                si = {x: None for x in fieldnames[8:13]}

            if '$FILE_NAME' in value:
                fn = {'FN creation time': value['$FILE_NAME']['Creation time'],
                      'FN modification time': value['$FILE_NAME']['Modification time'],
                      'FN entry modification time': value['$FILE_NAME']['Entry modification time'],
                      'FN last accessed time': value['$FILE_NAME']['Last accessed time'],
                      'Parent entry number': value['$FILE_NAME']['Parent entry number'],
                      'Filename': value['$FILE_NAME']['Filename']}
            else:
                fn = {x: None for x in fieldnames[14:19]}

            if '$DATA' in value:
                if 'Run list' in value['$DATA']:
                    d = {'Run list': value['$DATA']['Run list']}
                else:
                    d = {'Run list': ''}
            else:
                d = {'Run list': ''}

            writer.writerow(dict({'ID': entry,
                                  'FILE/BAAD': value['header']['FILE/BAAD'],
                                  'LSN': value['header']['$LogFile sequence number (LSN)'],
                                  'Hard link count': value['header']['Hard link count'],
                                  'Allocation flag': value['header']['Allocation flag'],
                                  'Allocation flag (verbose)': value['header']['Allocation flag (verbose)'],
                                  'Base record reference': value['header']['Base record reference'],
                                  'Entry number': value['header']['Entry number'], **si, **fn, **d}))

# This function is used to extract informations on bytes, typically attribute flags
def is_set(x, dict):
    return [dict[n] for n in range(16) if x & 1 << n != 0]

# Build the path of each entries file/dir recursively
# Can be then used to sort based on Path (ex. keep only C:\Users\)
def parse_tree(MFT):
    root_directory, root = 5, 'root'

    result = {}
    result[root_directory] = Path(root)
    p_ids, ids = [], []
    p_ids.append(root_directory)
    length = len(MFT)

    while 1:
        for k, entry in MFT.items():
            current_entry = entry['header']['Entry number']
            if '$FILE_NAME' in entry:
                parent_entry = entry['$FILE_NAME']['Parent entry number']
                current_filename = entry['$FILE_NAME']['Filename']
                if isinstance(current_filename, list):
                    current_filename = current_filename[1]

                if parent_entry in p_ids:
                    result[current_entry] = Path(result[parent_entry]) / current_filename
                    entry['header']['Path'] = str(Path(result[parent_entry])/current_filename)
                    ids.append(current_entry)
            else:
                result[current_entry] = ''

        p_ids = ids
        if len(result.keys()) == length:
            break

    return MFT

if __name__ == '__main__':
    pass
