### Céline Vanini
### 07.2022

'''
This script produces a pre-analysis for the digital stratigraphy analysis of a drive which was previously parsed
in the parser module (output = files in CSV format). It uses the treated MFT and boot files (CSV format).
The directory that is given as an input must contain the following files :
- MFT.csv
- boot.csv
- hash_list.csv

'''

#python .\rules.py -d "C:\Users\celin\UNIVERSITE\MA2S2\TdM\Results\COMFOR\process_image" -o "C:\Users\celin\UNIVERSITE\MA2S2\TdM\Results\COMFOR\process_image"


import os, math
from tqdm import tqdm
import time
import numpy as np
import logging
import pandas as pd
from pathlib import Path
import plotly.express as px
from datetime import datetime, timedelta
from argparse import ArgumentParser
from plotly_resampler import FigureResampler

pd.options.mode.chained_assignment = None  # default='warn'

########################################################################################################################
logger = logging.getLogger('rules')
event_logger = logging.getLogger('events')


########################################################################################################################
# Opening $Boot CSV file into dataframe for processing
def open_boot_file(dir):
    file = Path(f'{dir}\\boot.csv')
    if file.exists():
        logger.info('Reading the boot.csv file')
        boot = pd.read_csv(f'{dir}\\boot.csv', delimiter=',', encoding='utf-8')
        return boot
    else:
        logger.info('Error while processing the directory of the boot.csv file')
        raise Exception(f'No such file or directory : {dir}\\boot.csv')


def write_boot_info(df_boot, output):
    # with open(f"{output}/boot_info.txt", 'w') as f:
    # f.write('Volume information extracted from the boot.csv file :')

    info = list(zip(df_boot['Information'], df_boot['Value']))
    # f.write('\n' + '\n'.join([f'{x[0]} : {x[1]}' for x in info]))
    # sectors_per_clust = df_boot.loc[df_boot['Information'] == 'Sectors per cluster']['Value']
    # nb_sectors = df_boot.loc[df_boot['Information'] == 'Sectors count on volume']['Value']
    sectors_per_clust = int(df_boot.iloc[2]['Value'])
    nb_sectors = int(df_boot.iloc[3]['Value'])
    # f.write(f"\nNumber of clusters : {nb_sectors // sectors_per_clust}")
    return (nb_sectors // sectors_per_clust)


def boot_app(df_boot, df_MFT):
    # adding some information that should be presented in the report
    sectors_per_clust = int(df_boot.iloc[2]['Value'])
    nb_sectors = int(df_boot.iloc[3]['Value'])
    df_boot.loc[len(df_boot.index)] = ['Number of clusters', nb_sectors // sectors_per_clust]
    # temp = pd.DataFrame(['Number of clusters', 'Volume name', 'NTFS version'], [nb_sectors // sectors_per_clust, df_MFT.loc[3, 'Volume name'], df_MFT.loc[3, 'NTFS version']], columns=list('Information', 'Value'), index=[9, 10, 11])
    # df_boot.append({'Information': ['Number of clusters', 'Volume name', 'NTFS version'], 'Value': [nb_sectors // sectors_per_clust, df_MFT.loc[3, 'Volume name'], df_MFT.loc[3, 'NTFS version']]}, ignore_index=True)
    # df_boot.iloc[9] = ['Number of clusters', nb_sectors // sectors_per_clust]
    df_boot.loc[len(df_boot.index)] = ['Volume name', df_MFT.loc[3, 'Volume name']]
    df_boot.loc[len(df_boot.index)] = ['NTFS version', df_MFT.loc[3, 'NTFS version']]

    return df_boot


# Opening $MFT CSV file into dataframe for processing
def open_MFT_file(dir):
    file = Path(f'{dir}\\MFT.csv')
    logger.info('Reading the MFT.csv file')

    if file.exists():
        # damn it l'encodage était dur à trouver cp1252
        df_MFT = pd.read_csv(file, delimiter=',', low_memory=False, encoding='utf-8',
                             dtype={('ID', 'Sequence number', 'Hard link count', 'USN', 'Entry number',
                                     'Allocation flag', 'Base record entry number', 'Base record sequence number',
                                     'Parent entry number', 'First cluster', 'Resident', 'ADS resident',
                                     'ADS first cluster', 'Index first cluster'): int,
                                    ('Path', 'Filename', 'Filename2', 'Base record reference'): str})  #
        return df_MFT
    else:
        logger.info('Error while processing the directory of the MFT.csv file')
        raise Exception(f'No such file or directory : {dir}\\MFT.csv')


def pre_processing(df):
    logger.info('Pre-processing the MFT dataframe')
    df.fillna('', inplace=True)
    # handling timestamps for them to be a datetime object usable by pandas, dayfirst to avoid american format
    # coerce argument is used for cases where timestamps are like 01.01.1601
    df['SI creation time'] = pd.to_datetime(df['SI creation time'], errors='coerce', dayfirst=True)
    df['SI modification time'] = pd.to_datetime(df['SI modification time'], errors='coerce', dayfirst=True)
    df['SI entry modification time'] = pd.to_datetime(df['SI entry modification time'], errors='coerce', dayfirst=True)
    df['SI last accessed time'] = pd.to_datetime(df['SI last accessed time'], errors='coerce', dayfirst=True)
    df['FN creation time'] = pd.to_datetime(df['FN creation time'], errors='coerce', dayfirst=True)
    df['FN modification time'] = pd.to_datetime(df['FN modification time'], errors='coerce', dayfirst=True)
    df['FN entry modification time'] = pd.to_datetime(df['FN entry modification time'], errors='coerce', dayfirst=True)
    df['FN last accessed time'] = pd.to_datetime(df['FN last accessed time'], errors='coerce', dayfirst=True)

    df.rename(columns={'First cluster': 'DATA first cluster', 'Run list': 'DATA run list'}, inplace=True)
    first_cluster = ['DATA first cluster', 'ADS first cluster', 'Index first cluster']
    # Replacing NaN values by 0, indicates that those files/indexes are resident
    for column in first_cluster:
        df[column].fillna(0, inplace=True)
        df[column] = pd.to_numeric(df[column])

    # merging different run lists into one column for ploting
    df['First cluster'] = 0
    df.loc[df['DATA first cluster'] > 0, 'First cluster'] = df['DATA first cluster']
    df.loc[df['Index first cluster'] > 0, 'First cluster'] = df['Index first cluster']
    df.loc[df['ADS first cluster'] > 0, 'First cluster'] = df['ADS first cluster']
    # setting entry number as index to facilitate location in dataframe
    df.set_index('ID', inplace=True)
    # not forgetting the $Boot:
    df.loc[df.index == 7, 'First cluster'] = 0

    df['Events'] = 'None'

    return df


# test if an OS is installed by looking if some specific directories are present on the volume
# may not be always accurate, easy way to do this
def check_OS(df):
    type = any(
        [True for idx, row in df.iterrows() if
         '\programdata' in row['Path'].lower() or '\windows\system32' in row['Path'].lower()])
    return type


def open_nsrl_file(dir):
    file = Path(f'{dir}\\hash_list.csv')
    if file.exists():
        logger.info('Reading the hash_list.csv file')
        df_nsrl = pd.read_csv(f'{dir}\\hash_list.csv', delimiter=';')
        return df_nsrl
    else:
        logger.info('Error while processing the directory of the hash_list.csv file')
        raise Exception(f'No such file or directory : {dir}\\hash_list.csv')


# function used to flag system files with NSRL and path
def flag_system_files(df, df_nsrl):
    logger.info("Flagging system files (NSRL/Path)")
    # Filling NaN with None
    df_nsrl['Attr.'] = df_nsrl['Attr.'].fillna('None')
    # Dropping lines created by X-Ways for ADS and other attributes (keeping only 'real' files)
    df_nsrl.drop(df_nsrl[df_nsrl['Attr.'].str.endswith(')')].index, inplace=True)
    df_nsrl_ = df_nsrl.loc[df_nsrl['ID'].notna()]
    df_nsrl_['ID'] = df_nsrl_['ID'].astype(int)

    # Keeping only system files and appending the dataframe to the MFT one
    df_nsrl_only = df_nsrl_.loc[df_nsrl_['Hash set'] == 'NSRLFile']
    df_nsrl_only.set_index('ID', inplace=True)
    df_flag = pd.concat([df, df_nsrl_only], axis=1)
    # Filling non flagged files by 'None'
    df_flag['Hash set'] = df_flag['Hash set'].fillna('None')
    df_flag['Path_'] = df_flag['Path'].str.lower()

    # Adding flagging based on path or extension
    df_flag.loc[:, 'Flag'] = df_flag['Hash set']
    df_flag.loc[(df_flag['Path_'].str.startswith('root\program files')) & (df_flag['Flag'] == 'None'), 'Flag'] = 'Path'
    df_flag.loc[(df_flag['Path_'].str.startswith('root\programdata')) & (df_flag['Flag'] == 'None'), 'Flag'] = 'Path'
    df_flag.loc[(df_flag['Path_'].str.startswith('root\\boot')) & (df_flag['Flag'] == 'None'), 'Flag'] = 'Path'
    df_flag.loc[(df_flag['Path_'].str.startswith('root\perflogs')) & (df_flag['Flag'] == 'None'), 'Flag'] = 'Path'
    df_flag.loc[(df_flag['Path_'].str.startswith('root\intel')) & (df_flag['Flag'] == 'None'), 'Flag'] = 'Path'
    df_flag.loc[(df_flag['Path_'].str.startswith('root\documents')) & (df_flag['Flag'] == 'None'), 'Flag'] = 'Path'
    df_flag.loc[(df_flag['Path_'].str.startswith('root\dumpstack.log.tmp')) & (df_flag['Flag'] == 'None'), 'Flag'] = 'Path'
    df_flag.loc[(df_flag['Path_'].str.startswith('root\\recovery')) & (df_flag['Flag'] == 'None'), 'Flag'] = 'Path'
    df_flag.loc[(df_flag['Path_'].str.startswith('root\system volume information')) & (
            df_flag['Flag'] == 'None'), 'Flag'] = 'Path'
    df_flag.loc[(df_flag['Path_'].str.startswith('root\windows')) & (df_flag['Flag'] == 'None'), 'Flag'] = 'Path'

    df_flag.loc[(df_flag['Filename'].str.endswith('.dll')) & (df_flag['Flag'] == 'None'), 'Flag'] = 'Path'
    df_flag.loc[(df_flag['Filename'].str.endswith('.sys')) & (df_flag['Flag'] == 'None'), 'Flag'] = 'Path'
    df_flag.loc[:36, 'Flag'] = 'System file'
    df_flag.loc[df_flag['Parent entry number'].isin([x for x in range(36) if x != 5]), 'Flag'] = 'System file'
    df_flag.loc[df_flag['Path_'].str.startswith('root\\$'), 'Flag'] = 'System file'

    df_flag.loc[df_flag['Path_'].str.startswith('root\\user')  & (df_flag['Flag'] == 'None'), 'Flag'] = 'User'
    df_flag.loc[df_flag['Path_'].str.startswith('root\\$recycle'), 'Flag'] = 'User'
    df_flag['Filename_'] = df_flag['Filename'].str.lower()
    df_flag.loc[(df_flag['Path_'].str.contains('appdata') == True) & (df_flag['Path_'].str.startswith('root\\user')), 'Flag'] = 'AppData'
    df_flag.loc[(df_flag['Path_'].str.contains('prefetch') == True) & (df_flag['Filename'].str.endswith('.pf')), 'Flag'] = 'User'
    df_flag.loc[(df_flag['Path_'].str.contains('roaming')==True) & (df_flag['Path_'].str.startswith('root\\user')) & (df_flag['Path_'].str.contains('recent')==True) & (df_flag['Path_'].str.contains('appdata')==True), 'Flag'] = 'User'
    df_flag.loc[(df_flag['Filename_'].str.startswith('ntuser')), 'Flag'] = 'System file'

    l = ['$recycle.bin', 'documents', 'users', 'default', 'desktop', 'favorites', 'links', 'music', 'downloads',
         'pictures', 'saved games', 'videos', 'public', 'libraries', 'recent', 'mes documents', 'mes images',
         '3D objects', 'contacts', 'searches', 'links', 'mes images', 'voisinage réseau', 'menu démarrer', 'cookies']

    for e in l:
        df_flag.loc[df_flag['Filename_'] == e, 'Flag'] = 'System file'


    bin_entry = df_flag.loc[df_flag['Filename_'].str.startswith('$recycle')].index.values[0]
    df_flag.loc[bin_entry, 'Flag'] = 'System file'
    df_flag.loc[df_flag['Path_'].str.startswith('root\\users\\allus'), 'Flag'] = 'System file'
    df_flag.loc[df_flag['Path_'].str.startswith('root\\users\public'), 'Flag'] = 'System file'
    df_flag.loc[df_flag['Path_'].str.startswith('root\\users\defaul'), 'Flag'] = 'System file'
    df_flag.loc[df_flag['Filename_'].str.contains('customdes') == True, 'Flag'] = 'System file'
    df_flag.loc[df_flag['Filename_'].str.contains('automaticdes') == True, 'Flag'] = 'System file'
    df_flag.loc[(df_flag['Filename_'] == 'desktop.ini') & (
                df_flag['Parent entry number'] != bin_entry), 'Flag'] = 'System file'

    df_flag.loc[df_flag['Path'].str.contains('OBS')==True, 'Flag'] = 'System file'

    df_flag.loc[df_flag['Flag'] == 'System file', 'Events'] = 'System file'
    df_flag.loc[df_flag['Flag'] == 'NSRLFile', 'Events'] = 'System file'
    df_flag.loc[df_flag['Flag'] == 'Path', 'Events'] = 'System file'
    df_flag.loc[df_flag['Flag'] == 'AppData', 'Events'] = 'User'
    df_flag.loc[df_flag['Flag'] == 'User', 'Events'] = 'User'
    df_flag.loc[df_flag['Flag'] == 'None', 'Events'] = 'System file'

    return df_flag


def events(df):
    logger.info("Checking for specific events")
    OS = check_OS(df)
    # list with tuples like (timestamp, event_type, text)
    events = []
    events_no_date = []

    ####################################################################################################################
    install_date = df.iloc[0]['SI creation time']
    events_no_date.append((f'Volume has an OS installed: {OS}'))
    events.append(('', install_date, 'Formatting of the file system', 'System files were created on this date'))

    # MFT state
    if '),' in df.loc[0]['DATA run list']:
        events_no_date.append((f"The $MFT file is fragmented {df.loc[0]['DATA run list']}, can indicate the volume was once full"))
    else:
        events_no_date.append(
            (f"The $MFT file has the following run list: {df.loc[0]['DATA run list']}"))
    ####################################################################################################################

    # A difference is made based on the fact that the volume has an OS installed or not
    if OS is False:
        df_seq_1 = df.loc[df['Sequence number'] == 1]
        df_seq_1.reset_index(inplace=True)

        # TODO: handle this:
        df['Flag'] = 'None'
        df['Events'] = 'User'
        # first : checking if there are rows that have a timestamp before the formatting date (based on MFT timestamp)
        if (df['SI creation time'] < install_date).any():
            entries = list(df.loc[df['SI creation time'] < install_date]['Entry number'].values)
            if entries:
                if len(entries) == 1:
                    events.append(
                        ('', df.loc[entries[0]]['SI creation time'], 'Possible backdating/formatting',
                         f"Entry number {entries[0]} has a SI creation timestamp prior the file system installation date ({install_date.strftime('%d.%m.%Y %H:%M:%S')})"))
                else:
                    events.append(
                        ('', df.loc[entries[0]]['SI creation time'], 'Possible backdating/formatting',
                         f"Entries like number {entries[0]} have a SI creation timestamp prior the file system installation date ({install_date.strftime('%d.%m.%Y %H:%M:%S')})"))
        # no files prior this date, we continue
        else:
            pass

        # comparing each row with the precedent to see if there are any inconsistencies in timestamps
        # entry with number n was created before entry m if (n < m)
        # focusing on the creation timestamp
        # SEQ = 1
        df_seq_1['backdating'] = df_seq_1['SI creation time'].lt(df_seq_1['SI creation time'].shift())
        # value is True if the previous row in dataframe has a datetime > datetime considered
        if (df_seq_1['backdating'] == True).any():
            entries = list(df_seq_1.loc[df_seq_1['backdating'] == True]['Entry number'].values)

            for e in entries:
                df.loc[e, 'Events'] = 'Backdating'
                index_e = int(df_seq_1.loc[df_seq_1['Entry number'] == e].index[0])
                p_e = index_e - 1
                a_e = index_e + 1

                # defining upper_bound at which the action occured (taking the min between two possible values)
                next_lsn = df_seq_1.sort_values(by='LSN', ascending=False).loc[
                    df_seq_1['LSN'] > df_seq_1.loc[index_e]['LSN']].index.values[-1]
                upper_bound = min(
                    [df_seq_1.loc[index_e]['SI entry modification time'], df_seq_1.loc[next_lsn]['SI creation time']])

                # checking if it is only one file - to make the difference with clock drift
                # if p_e > e and a_e > p_e
                if df_seq_1.loc[p_e]['SI creation time'] > df_seq_1.loc[index_e]['SI creation time'] and \
                        df_seq_1.loc[a_e]['SI creation time'] > df_seq_1.loc[p_e]['SI creation time'] :
                    # propose an original creation time based on previous and next entries
                    creation_date_min = df_seq_1.loc[p_e]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')
                    creation_date_max = df_seq_1.loc[a_e]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')
                    events.append(('before ', upper_bound, 'file backdating',
                                   f"The file at entry {e} was backdated"
                                   f". Filename: {df_seq_1.loc[index_e]['Filename']}"
                                   f". File was originally created between {creation_date_min} and {creation_date_max}"))

                # can be a clock drift:
                else:
                    n = 0
                    while True:
                        # e is the entry that was flagged for the backdating
                        # now we check if subsequent files are also backdated compared to the entry before e
                        if df_seq_1.loc[index_e + n]['SI creation time'] >= df_seq_1.loc[p_e]['SI creation time']:
                            break
                        n += 1

                    nl = '\n\t'
                    drift_entries = [x for x in range(index_e, index_e + n)]
                    index_last_entry = max(drift_entries) + 1
                    last_entry = int(df_seq_1.loc[index_last_entry]['Entry number'])

                    # for the visualisations
                    for e in drift_entries:
                        df.loc[df['Entry number'] == df_seq_1.loc[e]['Entry number'], 'Events'] = 'Clock drift'

                    time_interval = (
                    df_seq_1.loc[index_e]['SI creation time'], df_seq_1.loc[index_last_entry]['SI creation time'])
                    # drift_realloc = list(df.loc[(df['Sequence number'] == 2) & (df['SI creation time'] > df_seq_1[e]['SI creation time']) & (df['SI creation time'] < df_seq_1[e]['SI creation time'])].index.values)

                    # We use the time of the previous entry with SEQ = 1 so may not be accurate
                    events.append(('after ', df_seq_1.loc[p_e]['SI creation time'], 'clock drift',
                                   f"Clock was changed for {df_seq_1.loc[index_e]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')}"
                                   f". During the clock drift, the following events happened: "
                                   f"\n\t{nl.join(['Creation of ' + df_seq_1.loc[x]['Filename'] + ' at ' + df_seq_1.loc[x]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S') for x in drift_entries])}"
                                   f"\n{'Clock was then changed for a time around : ' + df_seq_1.loc[index_last_entry]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S') if index_last_entry != df.iloc[-1]['Entry number'] else ''}"))

        ################################################################################################################
        # deletion (SEQ = 2)
        # TODO: gérer quand dans le time interval
        entries_seq_2 = list(
            df.loc[(df['Sequence number'] == 2) & (df['Entry number'] > 15)]['Entry number'].index.values)
        entries_seq_1 = list(
            df.loc[(df['Sequence number'] == 1) & (df['Entry number'] > 15)]['Entry number'].index.values)

        for entry in entries_seq_2:
            df.loc[entry, 'Events'] = 'Entry re-allocation'
            # creation time of the file
            p_e = max([x for x in entries_seq_1 if x < entry])
            n_e = min([x for x in entries_seq_1 if x > entry])
            # deletion time of the file
            p_t = max([x for x in entries_seq_1 if df.loc[x]['SI creation time'] < df.loc[entry]['SI creation time']])
            deletion_t_min = df.loc[p_t]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')
            deletion_t_max = df.loc[entry]['SI creation time']
            # a file cannot have been created after it was reallocated
            # as we consider SEQ = 1 here, interval of creation is defined by previous and next entries with this seq
            creation_t_min = df.loc[p_e]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')
            creation_t_max = df.loc[n_e]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')

            events.append(('', deletion_t_max, 'deletion',
                           f"Entry {entry} was reallocated (SEQ = 2). "
                           f"A file was deleted between {deletion_t_min} and {deletion_t_max.strftime('%d.%m.%Y %H:%M:%S')}. "
                           f"The file had a creation timestamp between {creation_t_min} and {creation_t_max}"))

        entries_seq_n = list(
            df.loc[(df['Sequence number'] > 2) & (df['Entry number'] > 15)]['Entry number'].index.values)

        for entry in entries_seq_n:
            df.loc[entry, 'Events'] = 'Entry re-allocation'
            p_t = max([x for x in entries_seq_1 if df.loc[x]['SI creation time'] < df.loc[entry]['SI creation time']])
            deletion_t_min = df.loc[p_t]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')
            deletion_t_max = df.loc[entry]['SI creation time']
            seq = df.loc[entry]['Sequence number']

            p_e = max([x for x in entries_seq_1 if x < entry])
            n_e = min([x for x in entries_seq_1 if x > entry])

            creation_t_min = df.loc[p_e]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')
            creation_t_max = df.loc[n_e]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')

            events.append(('', deletion_t_max, 'deletion',
                           f"Entry {entry} was reallocated (SEQ = {seq}). "
                           f"A file (SEQ = {seq-1}) was deleted between {deletion_t_min} and {deletion_t_max.strftime('%d.%m.%Y %H:%M:%S')}."))

            events_no_date.append((f"The file existing during the first generation (SEQ = 1) of entry {entry} had a creation timestamp "
                           f"between {creation_t_min} and {creation_t_max}"))


        ################################################################################################################
        # Using the allocation flag to spot which entries were marked as deleted. It is assumed that the entry is not
        # modified after it was marked
        entries_flag_0 = list(df.loc[(df['Allocation flag'] == 0) & (df['SI entry modification time'].notna()==True)][
                                  'Entry number'].index.values)
        entries_flag_2 = list(df.loc[(df['Allocation flag'] == 2) & (df['SI entry modification time'].notna()==True)][
                                  'Entry number'].index.values)

        events.extend([('', df.loc[entry]['SI entry modification time'], 'deletion (flag)',
                        f"The file {df.loc[entry]['Filename']} was marked as deleted (entry : {entry} ; "
                        f"path : {df.loc[entry]['Path']})") for entry in entries_flag_0])
        events.extend([('', df.loc[entry]['SI entry modification time'], 'deletion (flag)',
                        f"The directory {df.loc[entry]['Filename']} was marked as deleted (entry : {entry} ; "
                        f"path : {df.loc[entry]['Path']})") for entry in entries_flag_2])

    ####################################################################################################################
    # with OS
    else:
        df_seq_1 = df.loc[(df['Sequence number'] == 1)]
        df_seq_1.reset_index(inplace=True)
        # here we add as a condition that the file is not flagged as a system file
        n = '\n\t-'

        all_entries = []
        # First checking files that have a date
        if ((df['SI creation time'] < install_date) & (df['Flag'] == 'User')).any():

            entries = list(df.loc[(df['SI creation time'] < install_date) & (df['Flag'] == 'User')]['Entry number'].values)
            all_entries.extend(entries)
            # df.loc[e, 'Events'] = 'Possible backdating'
            if entries:
                if len(entries) == 1:
                    events.append(
                        ('', df.loc[entries[0]]['SI creation time'], 'Possible backdating/formatting',
                         f"{'File ' + df.loc[entries[0]]['Filename'] if df.loc[entries[0]]['Allocation flag'] == 1 else 'Index' + df.loc[entries[0]]['Filename']} "
                         f"(entry {entries[0]}) has a SI creation timestamp prior the file system installation date ({install_date.strftime('%d.%m.%Y %H:%M:%S')})"))
                else:
                    #print([df.loc[e]['Path'] for e in entries])
                    #print('\n'.join([df.loc[e-1]['FN creation time'].strftime('%d.%m.%Y %H:%M:%S') + '/' + df.loc[e]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S') +  '/' + df.loc[e+1]['FN creation time'].strftime('%d.%m.%Y %H:%M:%S') for e in entries]))
                    events.append(
                        ('', df.loc[entries[0]]['SI creation time'], 'Possible backdating/formatting',
                         f"Several entries have a SI creation timestamp prior the file system installation date ({install_date.strftime('%d.%m.%Y %H:%M:%S')}). "
                         f"The following files/indexes are concerned:\n{n.join(['[Entry ' + str(x) + '] ' + df.loc[x]['Path'] + ' (creation time: ' + df.loc[x]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S') + ')' for x in entries])}\n"))

        # comparing each row with the precedent to see if there are any inconsistencies in timestamps
        # entry with number n was created before entry m if (n < m)
        # focusing on the creation timestamp
        # SEQ = 1
        df_seq_1['backdating'] = df_seq_1['FN creation time'].lt(df_seq_1['FN creation time'].shift())
        # value is True if the previous row in dataframe has a datetime > datetime considered
        if (df_seq_1['backdating'] == True).any():
            entries = list(df_seq_1.loc[(df_seq_1['backdating'] == True) & (df['Events'] == 'User')]['Entry number'].values)

            for e in entries:
                if df.loc[e]['Events'] == 'User':
                    df.loc[e, 'Events'] = 'Backdating'
                    index_e = int(df_seq_1.loc[df_seq_1['Entry number'] == e].index[0])
                    p_e = index_e - 1
                    a_e = index_e + 1

                    # defining upper_bound at which the action occured (taking the min between two possible values)
                    next_lsn = df_seq_1.sort_values(by='LSN', ascending=False).loc[df_seq_1['LSN'] > df_seq_1.loc[index_e]['LSN']].index.values[-1]
                    upper_bound = min([df_seq_1.loc[index_e]['SI entry modification time'], df_seq_1.loc[next_lsn]['FN creation time']])

                    # checking if it is only one file - to make the difference with clock drift
                    # if p_e > e and a_e > p_e
                    if df_seq_1.loc[p_e]['FN creation time'] > df_seq_1.loc[index_e]['SI creation time'] and \
                            df_seq_1.loc[a_e]['FN creation time'] > df_seq_1.loc[p_e]['FN creation time']:
                        # propose an original creation time based on previous and next entries
                        creation_date_min = df_seq_1.loc[p_e]['FN creation time'].strftime('%d.%m.%Y %H:%M:%S')
                        creation_date_max = df_seq_1.loc[a_e]['FN creation time'].strftime('%d.%m.%Y %H:%M:%S')
                        events.append(('before ', upper_bound, 'file backdating',
                                       f"The file at entry {e} was backdated"
                                       f". Filename: {df_seq_1.loc[index_e]['Filename']}"
                                       f". File was originally created between {creation_date_min} and {creation_date_max}"))

                    # can be a clock drift:
                    else:
                        n = 0
                        while True:
                            # e is the entry that was flagged for the backdating
                            # now we check if subsequent files are also backdated compared to the entry before e
                            if df_seq_1.loc[index_e + n]['SI creation time'] >= df_seq_1.loc[p_e]['FN creation time']:
                                break
                            n += 1

                        nl = '\n\t'
                        drift_entries = [x for x in range(index_e, index_e + n)]
                        index_last_entry = max(drift_entries) + 1
                        last_entry = int(df_seq_1.loc[index_last_entry]['Entry number'])

                        # for the visualisations
                        for e in drift_entries:
                            df.loc[df['Entry number'] == df_seq_1.loc[e]['Entry number'], 'Events'] = 'Clock drift'

                        time_interval = (df_seq_1.loc[index_e]['SI creation time'], df_seq_1.loc[index_last_entry]['SI creation time'])
                        # drift_realloc = list(df.loc[(df['Sequence number'] == 2) & (df['SI creation time'] > df_seq_1[e]['SI creation time']) & (df['SI creation time'] < df_seq_1[e]['SI creation time'])].index.values)

                        # We use the time of the previous entry with SEQ = 1 so may not be accurate
                        events.append(('after ', df_seq_1.loc[p_e]['FN creation time'], 'clock drift',
                                       f"Clock was changed for {df_seq_1.loc[index_e]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')}"
                                       f". During the clock drift, the following events happened: "
                                       f"\n\t{nl.join(['File ' + df_seq_1.loc[x]['Filename'] + ' was created at ' + df_seq_1.loc[x]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S') for x in drift_entries if isinstance(x, datetime)])}"
                                       f"\n{'Clock was then changed for a time around : ' + df_seq_1.loc[index_last_entry]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S') if index_last_entry != df.iloc[-1]['Entry number'] else ''}"))
        else:
            pass
        # entries_seq_2 = list(
        #     df.loc[(df['Sequence number'] == 2) & (df['Entry number'] > 15)]['Entry number'].index.values)
        # entries_seq_1 = list(
        #     df.loc[(df['Sequence number'] == 1) & (df['Entry number'] > 15)]['Entry number'].index.values)
        #
        # for entry in tqdm(entries_seq_2):
        #     df.loc[entry, 'Events'] = 'Entry re-allocation'
        #     # creation time of the file
        #     p_e = max([x for x in entries_seq_1 if x < entry])
        #     n_e = min([x for x in entries_seq_1 if x > entry])
        #     # deletion time of the file
        #     p_t = max([x for x in entries_seq_1 if df.loc[x]['SI creation time'] < df.loc[entry]['SI creation time']])
        #     deletion_t_min = df.loc[p_t]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')
        #     deletion_t_max = df.loc[entry]['SI creation time']
        #     # a file cannot have been created after it was reallocated
        #     # as we consider SEQ = 1 here, interval of creation is defined by previous and next entries with this seq
        #     creation_t_min = df.loc[p_e]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')
        #     creation_t_max = df.loc[n_e]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')
        #
        #     events.append(('', deletion_t_max, 'deletion',
        #                    f"Entry {entry} was reallocated (SEQ = 2). "
        #                    f"A file was deleted between {deletion_t_min} and {deletion_t_max.strftime('%d.%m.%Y %H:%M:%S')}. "
        #                    f"The file had a creation timestamp between {creation_t_min} and {creation_t_max}"))
        #
        # entries_seq_n = list(
        #     df.loc[(df['Sequence number'] > 2) & (df['Entry number'] > 15)]['Entry number'].index.values)
        #
        # for entry in entries_seq_n:
        #     df.loc[entry, 'Events'] = 'Entry re-allocation'
        #     p_t = max([x for x in entries_seq_1 if df.loc[x]['SI creation time'] < df.loc[entry]['SI creation time']])
        #     deletion_t_min = df.loc[p_t]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')
        #     deletion_t_max = df.loc[entry]['SI creation time']
        #     seq = df.loc[entry]['Sequence number']
        #
        #     p_e = max([x for x in entries_seq_1 if x < entry])
        #     n_e = min([x for x in entries_seq_1 if x > entry])
        #
        #     creation_t_min = df.loc[p_e]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')
        #     creation_t_max = df.loc[n_e]['SI creation time'].strftime('%d.%m.%Y %H:%M:%S')
        #
        #     events.append(('', deletion_t_max, 'deletion',
        #                    f"Entry {entry} was reallocated (SEQ = {seq}). "
        #                    f"A file (SEQ = {seq - 1}) was deleted between {deletion_t_min} and {deletion_t_max.strftime('%d.%m.%Y %H:%M:%S')}."))
        #
        #     events_no_date.append(
        #         (f"The file existing during the first generation (SEQ = 1) of entry {entry} had a creation timestamp "
        #          f"between {creation_t_min} and {creation_t_max}"))

        ################################################################################################################
        # Using the allocation flag to spot which entries were marked as deleted. It is assumed that the entry is not
        # modified after it was marked
        # TODO : quid des .pf ?
        entries_flag_0 = list(df.loc[(df['Allocation flag'] == 0) & (
            df['SI entry modification time'].notna()==True) & (df['Flag'] == 'User')][
                                  'Entry number'].index.values)
        entries_flag_2 = list(df.loc[(df['Allocation flag'] == 2) & (
            df['SI entry modification time'].notna()==True) & (df['Flag'] == 'User')][
                                  'Entry number'].index.values)

        events.extend([('', df.loc[entry]['SI entry modification time'], 'deletion (flag)',
                        f"The file {df.loc[entry]['Filename']} was marked as deleted (entry : {entry} ; "
                        f"path : {df.loc[entry]['Path']})") for entry in entries_flag_0])
        events.extend([('', df.loc[entry]['SI entry modification time'], 'deletion (flag)',
                        f"The directory {df.loc[entry]['Filename']} was marked as deleted (entry : {entry} ; "
                        f"path : {df.loc[entry]['Path']})") for entry in entries_flag_2])

        # si SI < install_date AND flag != system:
        # potentiel backdating
        # si SI < install_date AND flag != system AND n-1 > n :
        # si SI < install_date AND flag != system AND n-1 > n AND n+1 < n:
        # si SI < install_date AND flag != system AND n-1 > n AND n+1 < n AND LSN(n-1) < n AND LSN(n+1) < n:
        # si SI < install_date AND flag != system AND n-1 > n AND n+1 < n AND LSN(n-1) < n AND LSN(n+1) < n :

        # date de création d'origine : regarder 1er n précédent avec SEQ=1 puis n d'après

    ####################################################################################################################
    # recycle bin
    # no point to make a difference between OS or not with recycle_bin events
    bin, bin_entry, ini_entry, sids = recycle_bin(df)
    if bin_entry:
        events.append(('', df.loc[bin_entry]['FN creation time'], 'recycle bin',
                       'The $RECYCLE.BIN directory was created'))
        df.loc[bin_entry, 'Events'] = 'Recycle bin'

        if sids:
            sids_dir = [('', df.loc[k]['SI creation time'], 'recycle bin', f'The directory {v} was created') for k, v in
                        sids.items()]
            df.loc[df['Entry number'].isin(sids.keys()), 'Events'] = 'Recycle bin'
            events.extend(sids_dir)

            sids_updated = []
            for sid in sids:
                if df.loc[sid]['SI creation time'] == df.loc[sid]['SI entry modification time']:
                    sids_updated.append(False)
                else:
                    sids_updated.append(True)

            if ini_entry:
                df.loc[ini_entry, 'Events'] = 'Recycle bin'
                if df.loc[ini_entry]['SI creation time'] == df.loc[ini_entry]['SI last accessed time']:
                    events_no_date.append(('[recycle bin] Note : the $RECYCLE.BIN directory was never emptied'))
                else:
                    if True not in sids_updated and df.loc[ini_entry]['SI last accessed time'] != df.loc[ini_entry]['SI creation time']:
                        events.append(('', df.loc[ini_entry]['SI last accessed time'], 'ctrl+shift', 'CTRL+SHIFT was performed for the last time'))

                    else:
                        events.append(('', df.loc[ini_entry]['SI last accessed time'], 'recycle bin/ctrl+shift',
                                       'The $RECYCLE.BIN directory was emptied for the last time/CTRL+SHIFT was performed for '
                                       'the last time'))

        if bin:
            # deleted_time, filename_R, entry_R, filename_I, entry_I
            bin_events = [('', file[0], 'recycle bin', f"The file {file[1]} was moved to the $RECYCLE.BIN by user"
                                                       f" {sids[df.loc[file[2]]['Parent entry number']]}. "
                                                       f"Corresponding $I entry: {file[-1]}") for file in bin]
            events.extend(bin_events)

    else:
        events_no_date.append("There is no $RECYCLE.BIN directory. Meaning that CTRL+SHIFT was never performed "
                              "and the recycle bin never used")

    ####################################################################################################################
    # root access
    events.append(('', df.loc[5]['SI entry modification time'], 'root directory',
                   'Content in the root directory was last changed'))
    events.append(('', df.loc[5]['SI last accessed time'], 'root directory',
                   'Root directory was last accessed'))

    ####################################################################################################################

    # sorting based on creation timestamp
    events.sort(key=lambda x: x[1])
    return events, events_no_date


def recycle_bin(df):
    # recycle_entry = [row['Entry number'] for idx, row in df.iterrows() if row['Filename'] == '$RECYCLE.BIN']
    try:
        recycle_entry = df.loc[df['Filename'].str.lower() == "$recycle.bin", 'Entry number'].index.values[0]
        desktop_ini = df.loc[df['Filename'] == 'desktop.ini', 'Entry number'].index.values[0]

        if recycle_entry:
            # print(f'Entry number of the $RECYCLE.BIN directory: {recycle_entry}')
            sids = {int(row['Entry number']): row['Filename'] for idx, row in df.iterrows() if
                    row['Parent entry number'] == recycle_entry}
            # print(f"The $RECYCLE.BIN contains the following folders:")
            # print('\n\t'.join([x for x in sids.values()]))
            r = []
            i = []
            for idx, row in df.iterrows():
                if row['Parent entry number'] in sids.keys():
                    if row['Filename'].startswith('$R'):
                        r.append((row['Entry number'], row['Filename']))
                        df.loc[row['Entry number'], 'Events'] = 'Recycle bin'
                        # df.loc[df['Entry number'] == row['Entry number'], 'Events'] = 'Recycle bin'
                    if row['Filename'].startswith('$I'):
                        i.append((row['Entry number'], row['Filename']))
                        df.loc[row['Entry number'], 'Events'] = 'Recycle bin'
                        # df.loc[df['Entry number'] == row['Entry number'], 'Events'] = 'Recycle bin'

            r.sort(key=lambda x: x[1])
            i.sort(key=lambda x: x[1])

            bin_content = []
            for id, file in enumerate(r):
                deleted_time = df.loc[i[id][0], 'SI creation time']
                # deleted_time, filename_R, entry_R, filename_I, entry_I
                bin_content.append((deleted_time, file[1], file[0], i[id][1], i[id][0]))
            return bin_content, recycle_entry, desktop_ini, sids
        else:
            return '', '', '', ''
    except IndexError:
        return '', '', '', ''


def write_events(events, events_no_date, output):
    with open(f"{output}\\events.txt", 'w') as f:
        # list with tuples like (timestamp, event_type, text)
        event_no_date = '\n'.join([x for x in events_no_date])
        event = '\n'.join(
            [f"[{event[0] + event[1].strftime('%d.%m.%Y %H:%M:%S')}] [{event[2]}] {event[3]}" for event in events])
        f.write(event_no_date + '\n')
        f.write('\n' + event)


########################################################################################################################
# Graphs
def add_timedelta(df):
    SI = list(df.loc[df['SI creation time'].notna() == True]['SI creation time'].sort_values())
    min, max = SI[0], SI[-1]
    delta = max - min

    if delta.seconds <= 7200:
        add = timedelta(minutes=1)
        range = '%H:%M:%S'
    elif delta.seconds > 7200 and delta.days <= 1:
        add = timedelta(minutes=30)
        range = '%H:%M:%S'
    # if events happened the same week
    elif delta.days <= 7 and delta.days > 1:
        add = timedelta(days=1)
        range = '%d.%m.%Y' #%H:%M:%S'
    # events happened the same year
    elif delta.days > 7 and delta.days < 365:
        add = timedelta(weeks=1)
        range = '%d.%m.%Y'
    elif delta.days > 365 and delta.days < 730:
        add = timedelta(weeks=4)
        range = '%d.%m.%Y'
    elif delta.days > 730 and delta.days < 1460:
        add = timedelta(weeks=8)
        range = '%d.%m.%Y'
    else:
        add = timedelta(weeks=26)
        range = '%d.%m.%Y'

    return add, range


def graph_SI_cluster_(df, output, clus):
    time.sleep(2)
    SI = list(df.loc[df['SI creation time'].notna() == True]['SI creation time'].sort_values())
    delta, range = add_timedelta(df)

    fig = FigureResampler(px.scatter(
        df.sort_values(by='First cluster'),
        x="First cluster",
        y='SI creation time',
        height=600,
        width=1000,
        color='Events',
        color_discrete_map={
            'User': 'rgba(8,140,240,0.8)',
            'Entry re-allocation': 'rgba( 255,87,87,1)',
            'Backdating': 'rgba(255,123,146,1)',
            'Clock drift': 'rgba(0,225,153,1)',
            'Recycle bin': 'rgba(255,155,43,1)',
            'System file': 'rgba(181,181,181,0.7)',
        },
        custom_data=['Entry number', 'Flag'],
        labels=dict(x='Premier cluster fichier/index', y='SI creation', ),
    ))

    # fillcolor='#e7f6fe', opacity=0.5
    # fig.add_hline(y=df.loc[0]['SI creation time'], line_width=1, line_dash="dash", line_color="black", opacity=0.6)

    fig.update_traces(
        marker={'size': 4,},
        showlegend=True,
        hovertemplate="<br>".join([
            #"<b>%{customdata[1]}</b>",
            "<b>%{customdata[0]}</b>",
            "Flag : %{customdata[2]}",
            "Timestamp: %{y}",
            "First cluster: %{x}",
        ])
    )
    # for e in fig['data']:
    #     e['hovertemplate']='<b>%{meta}</b><br>Entry number: %{x}<br>SI creation time: %{text}<extra></extra>'

    fig.update_layout(
        plot_bgcolor='white',
        hovermode="x",
        hoverlabel=dict(bgcolor='white', ),
        font=dict(color='#072f5f', size=14),
        yaxis_tickformat='%d.%m.%Y',
        xaxis_tickformat='d',
        xaxis_title="Position on the volume (First cluster)",
        yaxis_title="File creation timestamp (SI)",
        showlegend=True,
        # range=[datetime(2022,4,11,18,55), datetime(2022,4,11,18,59)]
    )
    # marker_line_width=0.5
    fig.update_xaxes(
        title_font_color='#072f5f',
        color='black',
        linecolor='black',
        gridcolor='#f0f3f4',
        mirror=False,
        showgrid=True,
        zeroline=False,
        range=[-1, clus + 10 * (round(math.log(clus)) - 1)]
    )
    fig.update_yaxes(
        title_font_color='#072f5f',
        color='black',
        linecolor='black',
        gridcolor='#f0f3f4',
        mirror=False,
        showgrid=True,
        zeroline=False,
        range=[SI[0], SI[-1] + delta]
    )



    fig.write_image(f"C:\\Users\celin\\UNIVERSITE\MA2S2\TdM\ForensicTools\\treatments\Graphs\supp\SI_cluster.pdf", format='pdf')
    time.sleep(2)


def graph_SI_entry(df, output):
    output = str(output)
    nb_entry = list(df['Entry number'].sort_values())[-1] + 10
    SI = list(df.loc[df['SI creation time'].notna() == True]['SI creation time'].sort_values())
    delta, range = add_timedelta(df)
    # df.to_string(columns=['Filename'], encoding='utf-16')

    fig = FigureResampler(px.scatter(
        df,
        x="Entry number",
        y='SI creation time',
        height=600,
        width=1000,
        color='Events',
        color_discrete_map={
            'User': 'rgba(8,140,240,0.8)',
            'Entry re-allocation': 'rgba(255,87,87,1)',
            'Backdating': 'rgba(255,123,146,1)',
            'Clock drift': 'rgba(2,220,118,1)',
            'Recycle bin': 'rgba(255,155,43,1)',
            'System file': 'rgba(210,210,210,0.7)',
        },
        labels=dict(x='Premier cluster fichier/index', y='SI creation'),
        custom_data=['First cluster', 'Flag']
    ))

    # fillcolor='#e7f6fe', opacity=0.5
    # fig.add_hline(y=df.loc[0]['SI creation time'], line_width=1, line_dash="dash", line_color="black", opacity=0.6)

    fig.update_traces(
        marker={'size': 4, },
        #TODO
        showlegend=True,
        hovertemplate="<br>".join([
            "<b>%{customdata[2]}</b>",
            "<b>%{customdata[0]}</b>",
            "Flag : %{customdata[1]}",
            "Timestamp: %{y}",
            "Entry number: %{x}",
        ])
    )

    fig.update_layout(
        plot_bgcolor='white',
        hovermode="x",
        hoverlabel=dict(bgcolor='white', ),
        font=dict(color='#072f5f', size=14),
        yaxis_tickformat=range,
        xaxis_tickformat='d',
        xaxis_title="Entry number in the MFT",
        yaxis_title="File creation timestamp (SI)",
        showlegend=True,
    )

    fig.update_xaxes(
        title_font_color='#072f5f',
        color='black',
        linecolor='black',
        gridcolor='#f0f3f4',
        mirror=False,
        showgrid=True,
        zeroline=False,
        range=[-1, nb_entry]
    )
    fig.update_yaxes(
        title_font_color='#072f5f',
        color='black',
        linecolor='black',
        gridcolor='#f0f3f4',
        mirror=False,
        showgrid=True,
        zeroline=False,
        range=[SI[0], SI[-1] + delta]
    )

    fig.write_image(f"{output}/SI_entry.pdf", format='pdf')
    fig.write_html(f"{output}/SI_entry.html")


def graph_SI_cluster(df, output, clus):
    time.sleep(2)
    SI = list(df.loc[df['SI creation time'].notna() == True]['SI creation time'].sort_values())
    delta, range = add_timedelta(df)

    fig = FigureResampler(px.scatter(
        df.sort_values(by='First cluster'),
        x="First cluster",
        y='SI creation time',
        height=600,
        width=1300,
        color='Events',
        color_discrete_map={
            'User': 'rgba(8,140,240,0.8)',
            'Entry re-allocation': 'rgba(255,87,87,1)',
            'Backdating': 'rgba(255,123,146,1)',
            'Clock drift': 'rgba(2,220,118,1)',
            'Recycle bin': 'rgba(255,155,43,1)',
            'System file': 'rgba(181,181,181,0.7)',
        },
        custom_data=['Entry number', 'Flag'],
        labels=dict(x='Premier cluster fichier/index', y='SI creation', ),
    ))

    # fillcolor='#e7f6fe', opacity=0.5

    fig.update_traces(
        marker={'size': 4,},
        showlegend=True,
        hovertemplate="<br>".join([
            "<b>%{customdata[1]}</b>",
            "<b>%{customdata[0]}</b>",
            "Flag : %{customdata[2]}",
            "Timestamp: %{y}",
            "First cluster: %{x}",
        ])
    )
    # for e in fig['data']:
    #     e['hovertemplate']='<b>%{meta}</b><br>Entry number: %{x}<br>SI creation time: %{text}<extra></extra>'

    fig.update_layout(
        plot_bgcolor='white',
        hovermode="x",
        hoverlabel=dict(bgcolor='white', ),
        font=dict(color='#072f5f', size=14),
        yaxis_tickformat='%d.%m.%Y',
        xaxis_tickformat='d',
        xaxis_title="Position on the volume (First cluster)",
        yaxis_title="File creation timestamp (SI)",
        showlegend=True,
        # range=[datetime(2022,4,11,18,55), datetime(2022,4,11,18,59)]
    )
    # marker_line_width=0.5
    fig.update_xaxes(
        title_font_color='#072f5f',
        color='black',
        linecolor='black',
        gridcolor='#f0f3f4',
        mirror=False,
        showgrid=True,
        zeroline=False,
        range=[-1, clus + 10 * (round(math.log(clus)) - 1)]
    )
    fig.update_yaxes(
        title_font_color='#072f5f',
        color='black',
        linecolor='black',
        gridcolor='#f0f3f4',
        mirror=False,
        showgrid=True,
        zeroline=False,
        range=[SI[0], SI[-1] + delta]
    )



    fig.write_image(f"{output}/SI_cluster.pdf", format='pdf')
    time.sleep(2)
    fig.write_html(f"{output}/SI_cluster.html")
    time.sleep(2)


if __name__ == '__main__':
    parser = ArgumentParser(description='bloup')

    # parser.add_argument('-m', '--mft_file', help='$MFT file extracted from the live volume or image file in CSV format')
    # parser.add_argument('-b', '--boot_file', help='$Boot file extracted from the live volume or image file in CSV format')
    parser.add_argument('-d', '--directory', help='Path to the directory containing pre-treated files')
    parser.add_argument('-o', '--output', help='bloup')

    args = parser.parse_args()

    if not os.path.isdir(args.output):
        os.mkdir(args.output)

    logging.basicConfig(format='%(asctime)s - %(name)-12s: %(message)s',
                        datefmt='[%d.%m.%Y %H:%M:%S]', level=logging.INFO,
                        handlers=[logging.FileHandler(f'{args.output}\\rules.txt'), logging.StreamHandler()])

    logger.info('Starting to process')

    dir = Path(args.directory)
    if dir.is_dir():
        df_boot = open_boot_file(dir)
        clus = write_boot_info(df_boot, dir)
        #clus = 100000
        df_MFT = open_MFT_file(dir)
        df_MFT = pre_processing(df_MFT)

        OS = check_OS(df_MFT)
        if OS is True:
            df_nsrl = open_nsrl_file(dir)
            df_MFT = flag_system_files(df_MFT, df_nsrl)
        found_events, events_no_date = events(df_MFT)
        write_events(found_events, events_no_date, dir)
        graph_SI_cluster_(df_MFT, dir, clus)
        graph_SI_entry(df_MFT, dir)
        graph_SI_cluster(df_MFT, dir, clus)
        logger.info('Process finished !')
    else:
        raise Exception(f"The directory doesn't exists: {dir}")
