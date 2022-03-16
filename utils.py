import csv, json
from datetime import datetime, timedelta


def convert_filetime(date_to_convert: int):
    delta = timedelta(microseconds=date_to_convert / 10)
    win_date = datetime(1601, 1, 1, 0, 0, 0)
    timestamp = win_date + delta

    # TODO: gérer la timezone
    # besoin des millisecondes ?
    return f'{datetime.strftime(timestamp, "%d.%m.%Y %H:%M:%S +0000")}'


def MFT_to_json(dict, file):
    with open(file, 'w') as outfile_json:
        json.dump(dict, outfile_json, indent=4)


def MFT_to_csv(MFT, file):
    fieldnames = ['ID', 'FILE/BAAD', 'LSN', 'Hard link count', 'Allocation flag', 'Allocation flag (verbose)',
                  'Entry number', 'SI creation time', 'SI modification time', 'SI entry modification time',
                  'SI last accessed time', 'File type', 'FN creation time', 'FN modification time',
                  'FN entry modification time', 'FN last accessed time', 'Parent entry number', 'Filename', 'Run list']

    with open(file, 'w', newline='') as outfile_csv:
        writer = csv.DictWriter(outfile_csv, fieldnames=fieldnames)

        writer.writeheader()
        for entry, value in MFT.items():
            if '$STANDARD_INFORMATION' in value:
                si = {'SI creation time': value['$STANDARD_INFORMATION']['Creation time'],
                      'SI modification time': value['$STANDARD_INFORMATION']['Modification time'],
                      'SI entry modification time': value['$STANDARD_INFORMATION']['Entry modification time'],
                      'SI last accessed time': value['$STANDARD_INFORMATION']['Last accessed time'],
                      'File type': value['$STANDARD_INFORMATION']['File type']}
            else:
                si = {x: None for x in fieldnames[7:11]}

            if '$FILE_NAME' in value:
                fn = {'FN creation time': value['$FILE_NAME']['Creation time'],
                      'FN modification time': value['$FILE_NAME']['Modification time'],
                      'FN entry modification time': value['$FILE_NAME']['Entry modification time'],
                      'FN last accessed time': value['$FILE_NAME']['Last accessed time'],
                      'Parent entry number': value['$FILE_NAME']['Parent entry number'],
                      'Filename': value['$FILE_NAME']['Filename']}
            else:
                fn = {x: None for x in fieldnames[12:17]}

            if '$DATA' in value:
                if 'Run list' in value['$DATA']:
                    d = {'Run list': value['$DATA']['Run list']}
                else:
                    d = {'Run list': ''}

            writer.writerow(dict({'ID': entry,
                                  'FILE/BAAD': value['header']['FILE/BAAD'],
                                  'LSN': value['header']['$LogFile sequence number (LSN)'],
                                  'Hard link count': value['header']['Hard link count'],
                                  'Allocation flag': value['header']['Allocation flag'],
                                  'Allocation flag (verbose)': value['header']['Allocation flag (verbose)'],
                                  'Entry number': value['header']['Entry number']}, **(si | fn | d)))



def is_set(x, dict):
    return [dict[n] for n in range(16) if x & 1 << n != 0]


if __name__ == '__main__':
    pass
