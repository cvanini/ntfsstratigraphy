import pandas as pd
from datetime import datetime

type = {
    ('ID', 'Sequence number', 'Hard link count', 'USN', 'Entry number', 'Allocation flag', 'Base record entry number',
     'Base record sequence number', 'Parent entry number', 'First cluster', 'Resident', 'ADS resident',
     'ADS first cluster', 'Index first cluster'): int,
    ('Path', 'Filename', 'Filename2', 'Base record reference'): str
}


def open_(filename):
    date_parser = lambda x: datetime.strptime(x, "%m.%d.%Y %H:%M:%S %z")
    df = pd.read_csv(filename, encoding='utf-8', delimiter=',', low_memory=False, dtype=type,
                     date_parser={('SI creation time', 'SI modification time', 'SI entry modification time',
                                   'SI last accessed time', 'FN creation time', 'FN modification time',
                                   'FN entry modification time', 'FN last accessed time'): date_parser})

    df = df.set_index('ID')
    return df


def pre_processing(df):
    df.fillna('', inplace=True)
    df['Events'] = ''
    try:
        df['SI creation time'] = pd.to_datetime(df['SI creation time'])
        df['SI modification time'] = pd.to_datetime(df['SI modification time'])
        df['SI entry modification time'] = pd.to_datetime(df['SI entry modification time'])
        df['SI last accessed time'] = pd.to_datetime(df['SI last accessed time'])
        df['FN creation time'] = pd.to_datetime(df['FN creation time'])
        df['FN modification time'] = pd.to_datetime(df['FN modification time'])
        df['FN entry modification time'] = pd.to_datetime(df['FN entry modification time'])
        df['FN last accessed time'] = pd.to_datetime(df['FN last accessed time'])
    except Exception:
        pass

    first_cluster = ['First cluster', 'ADS first cluster', 'Index first cluster']
    # Replacing NaN values by 0, indicates that those files/indexes are resident
    for column in first_cluster:
        df[column].fillna(0, inplace=True)
        df[column] = pd.to_numeric(df[column])

    df['First cluster (all)'] = 0
    df.loc[df['First cluster'] > 0, 'First cluster (all)'] = df['First cluster']
    df.loc[df['Index first cluster'] > 0, 'First cluster (all)'] = df['Index first cluster']
    df.loc[df['ADS first cluster'] > 0, 'First cluster (all)'] = df['ADS first cluster']

    return df


def flag_system_files(df):
    # TODO: différencier OS avec non OS
    # TODO: NSRL
    df.loc[:35, 'Usage'] = 'System'
    df.loc[df['File type'].str.contains('System File'), 'Usage'] = 'System'
    df.loc[df['Path'].str.startswith("root\$"), 'Usage'] = 'System'
    df.loc[df['Path'].str.endswith('$MFT'), 'Usage'] = 'MFT'
    df.loc[df['Filename'].str.endswith('.lnk'), 'Usage'] = 'User'
    df.loc[df['Path'].str.startswith('root\\Users'), 'Usage'] = 'User'
    df.loc[df['Path'].str.contains('AppData'), 'Usage'] = 'System'
    df.loc[(df['Path'].str.contains('Roaming')) & df['Path'].str.startswith('root\\Users'), 'Usage'] = 'System'
    df.loc[df['Path'].str.startswith('root\Windows'), 'Usage'] = 'System'
    df.loc[df['Filename'].str.endswith('.dll'), 'Usage'] = 'System'
    df.loc[df['Filename'].str.endswith('.evtx'), 'Usage'] = 'System'
    df.loc[df['Path'].str.endswith('.pf'), 'Usage'] = 'System'
    df.loc[df['Path'].str.startswith('root\Program Files'), 'Usage'] = 'System'
    df.loc[df['Path'].str.startswith('root\ProgramData'), 'Usage'] = 'System'
    df.loc[df['Path'].str.startswith('root\PerfLogs'), 'Usage'] = 'System'
    df.loc[df['Path'].str.startswith('root\Intel'), 'Usage'] = 'System'
    df.loc[df['Path'].str.startswith('root\System Volume Information'), 'Usage'] = 'System'
    df['Usage'].fillna('Other', inplace=True)
    return df


# test if an OS is install by looking if some specific directories are present on the volume
# may not be always accurate
# TODO: complete?
def check_OS(df):
    type = any([True for idx, row in df.iterrows() if '\Program Files' in row['Path'] and '\Windows\system32' in row['Path']] )
    return type


def recycle_bin(df):
    recycle_entry = [row['Entry number'] for idx, row in df.iterrows() if row['Filename'] == '$RECYCLE.BIN']
    #recycle_entry = df.loc[df['Filename'] == "$RECYCLE.BIN", 'Entry number'].values[0]
    if recycle_entry:
        # print(f'Entry number of the $RECYCLE.BIN directory: {recycle_entry}')
        sids = {row['Entry number']: row['Filename'] for idx, row in df.iterrows() if
                row['Parent entry number'] == recycle_entry[0]}
        # print(f"The $RECYCLE.BIN contains the following folders:")
        # print('\n\t'.join([x for x in sids.values()]))
        r = []
        i = []
        for idx, row in df.iterrows():
            if row['Parent entry number'] in sids.keys():
                if row['Filename'].startswith('$R'):
                    r.append((row['Entry number'], row['Filename']))
                    #row['Events'] = 'Moved to the recycle bin'
                    df.loc[df['Entry number'] == row['Entry number'], 'Events'] = 'Recycle bin'
                if row['Filename'].startswith('$I'):
                    i.append((row['Entry number'], row['Filename']))
                    df.loc[df['Entry number'] == row['Entry number'], 'Events'] = 'Recycle bin'

        r.sort(key=lambda x: x[1])
        i.sort(key=lambda x: x[1])
        # deleted_files = list(zip(r, i))
        # text = []
        # # ((123, eueue), ())
        # for file in deleted_files:
        #     deleted_time = df.loc[file[1][0], 'SI creation time'].strftime('%d.%m.%Y %H:%M:%S %z')
        #     text.append(f"Deleted file: {file[0][1]}, corresponding $I: {file[1][1]} (deleted on {deleted_time})")

        text = []
        for id, file in enumerate(r):
            deleted_time = df.loc[i[id][0], 'SI creation time'].strftime('%d.%m.%Y %H:%M:%S %z')
            text.append((deleted_time, file[1], file[0], i[id][1], i[id][0]))


            #df.loc[i[id][0], 'Events'] = 'Moved to recycle bin'
            #df.loc[file[1], 'Events'] = 'Moved to recycle bin'

        return text, df

    else:
        return '', df


def deletion(df):
    df['Stratum'] = df['Sequence number'].astype(str)
    df.loc[df['Entry number'] < 36, 'Stratum'] = '0'
    df.loc[df['Sequence number'] == 1, 'Stratum'] = '1'
    df.loc[(df['Entry number'] > 36) & (df['Sequence number'] != 1), 'Stratum'] = '3'
    #df.loc[df['Sequence number'] == 2, 'Stratum'] = '2'
    #df['Stratum'] = df['Stratum'].astype(int)

    return df


def event(lists):
    pass


if __name__ == '__main__':
    pass
