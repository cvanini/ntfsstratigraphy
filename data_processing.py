import pandas as pd
from datetime import datetime

type = {
    ('ID', 'Sequence number', 'Hard link count', 'USN', 'Entry number', 'Allocation flag', 'Base record entry number',
     'Base record sequence number', 'Parent entry number', 'First cluster', 'Resident', 'ADS resident',
     'ADS first cluster', 'Index first cluster'): int,
    ('Path', 'Filename', 'Filename2', 'Base record reference'): str
}


def open_(filename):
    date_parser = lambda x: datetime.strptime(x, "%d.%m.%Y %H:%M:%S %z")
    df = pd.read_csv(filename, encoding='utf-8', delimiter=',', low_memory=False, dtype=type,
                     date_parser={('SI creation time', 'SI modification time', 'SI entry modification time',
                                   'SI last accessed time', 'FN creation time', 'FN modification time',
                                   'FN entry modification time', 'FN last accessed time'): date_parser})

    df = df.set_index('ID')
    return df


def pre_processing(df):
    df.fillna('', inplace=True)
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

if __name__ == '__main__':
    pass
