#### Céline Vanini
#### 02.03.2022

import copy
import csv
import json
import pytz
import struct
import logging
import itertools
from tqdm import tqdm
from pathlib import Path, WindowsPath
from datetime import datetime, timedelta

MFT_logger = logging.getLogger('MFT')


# Convert the Windows FILETIME timestamps to readable timestamps (UTC) (format : 01.01.1970 00:00:00 + 0000)
# Timestamps in entries are expressed in UTC (https://www.sciencedirect.com/topics/computer-science/master-file-table)
def convert_filetime(date_to_convert: int):
    try:
        delta = timedelta(microseconds=date_to_convert / 10)
        win_date = datetime(1601, 1, 1, 0, 0, 0)
        timestamp = win_date + delta

        # change to the timezone of the machine, to be defined if not relevant
        # in a try to convert incorrect timestamps to None (e.g 18.09.1616)
        # timestamp = timestamp.astimezone()

        if timestamp.year > 1970:
            return f'{datetime.strftime(timestamp, "%d.%m.%Y %H:%M:%S %z")}'
        else:
            return None
    except Exception:
        print(delta, win_date)
        return None
        pass


# method for parsing the bitmap attribute in the entry 0 of the $MFT, indicating the entries allocated
# used to check if the MFT.py does its job correctly ! (doesn't forget any entry)
def parse_bitmap_MFT(path):
    with open(f'{path}\\MFT_bitmap', 'rb') as file:
        data = file.read()
        res = list(itertools.chain.from_iterable([[1 if byte & 1 << n != 0 else 0 for n in range(8)] for byte in data]))
        bitmap_attribute = {n: res[n] for n in range(len(res)) if res[n] == 1}
        return len(bitmap_attribute)


# Save the dictionary containing the parsed MFT into a json file
def MFT_to_json(dir, dict):
    with open(f'{dir}\\MFT.json', 'w') as outfile_json:
        json.dump(dict, outfile_json, indent=4)


# Saving to csv file. The fields considered here are the ones used for the analysis on Tableau Software. For a full
# MFT analysis, the json function should be preferred.
def MFT_to_csv(dir, MFT):
    MFT_logger.info(f'Writting $MFT to CSV file.. this operation may take some time')

    fieldnames = ['ID', 'Sequence number', 'FILE/BAAD', 'LSN', 'Hard link count', 'Allocation flag',
                  'Allocation flag (verbose)', 'Entry number', 'Base record reference', 'Base record entry number',
                  'Base record sequence number', 'Path', 'SI creation time', 'SI modification time',
                  'SI entry modification time', 'SI last accessed time', 'File type', 'USN', 'FN creation time',
                  'FN modification time', 'FN entry modification time', 'FN last accessed time', 'Parent entry number',
                  'Filename', 'Filename2', 'Run list', 'First cluster', 'Resident', 'ADS Run list', 'ADS first cluster',
                  'ADS resident', 'Index flag', 'Index Run list', 'Index first cluster', 'Volume name', 'NTFS version']

    with open(f'{dir}\\MFT.csv', 'w', newline='', encoding='utf-8') as outfile_csv:
        writer = csv.DictWriter(outfile_csv, fieldnames=fieldnames, delimiter=',')

        writer.writeheader()
        for entry, value in tqdm(MFT.items(), desc='[csv]'):
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
                si = {x: None for x in fieldnames[12:17]}

            count = len([x for x in value if x.startswith('$FILE_NAME')])
            try:
                match count:
                    case 0:
                        # No filenames in the MFT entry
                        fn = {x: None for x in fieldnames[18:24]}
                    case 1:
                        fn = {'FN creation time': value['$FILE_NAME']['Creation time'],
                              'FN modification time': value['$FILE_NAME']['Modification time'],
                              'FN entry modification time': value['$FILE_NAME']['Entry modification time'],
                              'FN last accessed time': value['$FILE_NAME']['Last accessed time'],
                              'Parent entry number': value['$FILE_NAME']['Parent entry number'],
                              'Filename': value['$FILE_NAME']['Filename'],
                              'Filename2': ''}
                    case 2:
                        fn = {'FN creation time': value['$FILE_NAME']['Creation time'],
                              'FN modification time': value['$FILE_NAME']['Modification time'],
                              'FN entry modification time': value['$FILE_NAME']['Entry modification time'],
                              'FN last accessed time': value['$FILE_NAME']['Last accessed time'],
                              'Parent entry number': value['$FILE_NAME']['Parent entry number'],
                              'Filename': value['$FILE_NAME2']['Filename'],
                              'Filename2': value['$FILE_NAME']['Filename']}
                    case _:
                        pass
            except Exception:
                print(str(entry) + '\n' + str(value))

            if '$DATA' in value:
                if 'Run list' in value['$DATA']:
                    d = {'Run list': value['$DATA']['Run list'],
                         'First cluster': value['$DATA']['First cluster'],
                         'Resident': value['$DATA']['Resident']}
                else:
                    d = {'Run list': '', 'First cluster': '', 'Resident': value['$DATA']['Resident']}
            else:
                d = {'Run list': '', 'First cluster': '', 'Resident': ''}

            if 'ADS1' in value:
                if 'Run list' in value['ADS1']:
                    ads = {'ADS Run list': value['ADS1']['Run list'],
                           'ADS first cluster': value['ADS1']['First cluster'],
                           'ADS resident': value['ADS1']['Resident']}
                else:
                    ads = {'ADS Run list': '', 'ADS first cluster': '', 'ADS resident': ''}
            else:
                ads = {'ADS Run list': '', 'ADS first cluster': '', 'ADS resident': ''}

            if '$INDEX_ROOT' in value:
                ind = {'Index flag': value['$INDEX_ROOT']['Index flag']}
            else:
                ind = {'Index flag': ''}

            if '$INDEX_ALLOCATION' in value:
                if 'Data run' in value['$INDEX_ALLOCATION']:
                    all = {'Index Run list': value['$INDEX_ALLOCATION']['Data run'],
                           'Index first cluster': value['$INDEX_ALLOCATION']['First cluster']}
                else:
                    all = {'Index Run list': '', 'Index first cluster': ''}
            else:
                all = {'Index Run list': '', 'Index first cluster': ''}

            if '$VOLUME_NAME' in value:
                v_name = {'Volume name': value['$VOLUME_NAME']['Volume name']}
            else:
                v_name = {'Volume name': ''}

            if '$VOLUME_INFORMATION' in value:
                v_info = {'NTFS version': value['$VOLUME_INFORMATION']['NTFS version']}
            else:
                v_info = {'NTFS version': ''}

            if 'Path' in value['header']:
                path = value['header']['Path']
            else:
                path = ''

            writer.writerow(dict({'ID': entry,
                                  'Sequence number': value['header']['Sequence number'],
                                  'FILE/BAAD': value['header']['FILE/BAAD'],
                                  'LSN': value['header']['$LogFile sequence number (LSN)'],
                                  'Hard link count': value['header']['Hard link count'],
                                  'Allocation flag': value['header']['Allocation flag'],
                                  'Allocation flag (verbose)': value['header']['Allocation flag (verbose)'],
                                  'Base record reference': value['header']['Base record reference'],
                                  'Base record entry number': value['header']['Base record entry number'],
                                  'Base record sequence number': value['header']['Base record sequence number'],
                                  'Entry number': value['header']['Entry number'],
                                  'Path': path, **si, **fn, **d, **ads, **ind, **all, **v_name, **v_info}))

        MFT_logger.info(f'CSV file of the $MFT is written !')


# This function is used to extract information on bits, typically attribute flags
def is_set(x, dict):
    return [dict[n] for n in range(16) if x & 1 << n != 0]


# To unpack group of 6 bytes (not supported by the struct library)
def unpack6(x):
    x1, x2, x3 = struct.unpack('<HHH', x)
    return (x1 + (x2 << 16) + (x3 << 32))


# Build the path of each entries file/dir recursively
# Can be then used to sort based on Path (ex. keep only C:\Users\)
def parse_tree(MFT):
    MFT_logger.info("Starting reconstructing paths")
    # creating a working copy:: takes some time
    temp_MFT = copy.deepcopy(MFT)
    length = len(MFT)

    # Paths are stored on this dictionary :
    result = {}
    result[5] = Path('root')
    # Parents that already have their path found are appended to this list :
    p_ids = [5]

    n = 1

    # information concerning the parent entry is stored in the $FILE_NAME attribute.
    # The reconstruction starts from the root directory, which is entry number 5.
    while 1:
        MFT_logger.info(f"Iteration number {n}")
        for k, entry in tqdm(temp_MFT.items(), desc=f'[Path]'):
            # As there can be multiple filenames (cf. hard links):
            # p = []
            if '$FILE_NAME' in entry:
                for m in entry:
                    if m.startswith('$FILE_NAME'):
                        parent_entry = entry[m]['Parent entry number']
                        current_filename = entry[m]['Filename']

                        # TODO: hard links : plusieurs chemins pour une même entrée
                        # problème : certains fichiers ont des hard links à 6000
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
            MFT_logger.info(f"Number of reconstructed paths: {len(result.keys())}")
            # Le plus rapide ça reste le dictionnaire en compréhension
            MFT_logger.info("Reducing the dictionary of entries to find a path")
            # takes a lot of time :
            # for k in list(temp_MFT.keys()):
            #     if k not in p_ids:
            #         del temp_MFT[k]

            # to_delete = set(temp_MFT.keys()).difference(p_ids)
            # for d in to_delete:
            #     del temp_MFT[d]
            temp_MFT = {k: v for k, v in temp_MFT.items() if k not in p_ids}

        n += 1

    return MFT


if __name__ == '__main__':
    pass
