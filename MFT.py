#### Céline Vanini
#### 02.03.2021

'''MFT parser : extract the entries attributes informations based on offset values.
Principal attributes that can be recovered are $STANDARD_INFORMATION, $FILE_NAME and $DATA.
For the other attributes, only the header is parsed (rest of info not necessary in this context).
Will be managed afterwards.

Sources : File system forensic analysis (B. Carrier, 2005) and https://flatcap.github.io/linux-ntfs/ntfs/attributes/index.html
'''

import copy
import struct
from ressources.dict import *
from ressources.utils import *
from ressources.ProgressBar import printProgressBar
from argparse import ArgumentParser

MFT_RECORD_SIZE = 1024

MFT_record = {
    'header': '',
    '$STANDARD_INFORMATION': '',
    '$FILE_NAME': '',
    '$DATA': ''
}


# TODO: gérer les BAAD
# Gérer les non-base MFT entry (lorsque besoin de + d'une entrée pour stocker tous les attributs d'un fichier)
# -> ils vont avoir un $ATTRIBUTE_LIST (0x20000000)
def parse_header(header, raw_record):
    header.clear()
    if raw_record[:4] == b'\x42\x41\x41\44':
        print('bloup')
    if raw_record[:4] == b'\x00\x00\x00\x00':
        return None
    if raw_record[:4] != b'\x46\x49\x4C\x45':
        raise Exception("This is not the start of a MFT entry")

    header['FILE/BAAD'] = raw_record[:4].decode('utf-8')
    # header['Offset to update sequence'] = struct.unpack("<H", raw_record[4:6])[0]
    # Used by the file system log:
    header['$LogFile sequence number (LSN)'] = struct.unpack("<Q", raw_record[8:16])[0]
    # increments when the corresponding file is deleted
    header['Entry use counter'] = struct.unpack("<H", raw_record[16:18])[0]

    # Link count = how many directories referencing this MFT entry
    # If hard links were created for the file, this number is incremented by one for each link.
    header['Hard link count'] = struct.unpack("<H", raw_record[18:20])[0]
    # equivalent to the header size:
    header['First attribute offset'] = struct.unpack("<H", raw_record[20:22])[0]
    header['Allocation flag'] = struct.unpack("<H", raw_record[22:24])[0]

    if header['Allocation flag'] == 0:
        header['Allocation flag (verbose)'] = '00 (Deleted file)'
    elif header['Allocation flag'] == 1:
        header['Allocation flag (verbose)'] = '01 (Visible file)'
    elif header['Allocation flag'] == 2:
        header['Allocation flag (verbose)'] = '02 (Deleted directory)'
    elif header['Allocation flag'] == 3:
        header['Allocation flag (verbose)'] = '03 (Visible directory)'
    elif header['Allocation flag'] == 3:
        header['Allocation flag (verbose)'] = '04 (Extension)'
    # TODO: vérifier les valeurs, dit que 0x08 est spécial index
    elif header['Allocation flag'] in (8, 9, 10, 11, 12):
        header['Allocation flag (verbose)'] = '(Special index)'
    else:
        header['Allocation flag (verbose)'] = 'Unknown allocation flag'
        # raise Exception("Invalid value for Allocation flag - possible values (00, 01, 02, 03)")

    header['Entry logical size'] = struct.unpack("<I", raw_record[24:28])[0]
    header['Entry physical size'] = struct.unpack("<I", raw_record[28:32])[0]
    header['Base record reference'] = struct.unpack("<Q", raw_record[32:40])[0]
    header['Next attribute ID'] = struct.unpack("<H", raw_record[40:42])[0]
    header['Entry number'] = struct.unpack("<I", raw_record[44:48])[0]

    MFT_record['header'] = header

    return header


def parse_attribute_header(record, dict):
    # includes the header ~of the header
    dict['Attribute size'] = struct.unpack("<I", record[4:8])[0]
    dict['Resident'] = struct.unpack("<B", record[8:9])[0]
    dict['Attribute name length'] = struct.unpack("<B", record[9:10])[0]
    dict['Offset to name'] = struct.unpack("<H", record[10:12])[0]
    dict['Flags'] = struct.unpack("<H", record[12:14])[0]
    if dict['Flags'] == 1 :
        dict['Flags (verbose)'] = 'compressed'
    elif dict['Flags'] == 16384:
        dict['Flags (verbose)'] = 'encrypted'
    elif dict['Flags'] == 32768:
        dict['Flags (verbose)'] = 'sparse'
    elif dict['Flags'] == 0:
        pass
    else:
        dict['Flags (verbose)'] = 'unknown'

    dict['Attribute ID'] = struct.unpack("<H", record[14:16])[0]
    #dict['Content start offset'] = struct.unpack("<H", record[10:12])[0]

    '''Run List considered only in the $DATA attribute'''
    if dict['Resident'] == 0:
        dict['Resident (verbose)'] = '00 (Resident content)'
        # length of attribute without header
        dict['Content size'] = struct.unpack("<I", record[16:20])[0]
        dict['Content start offset (resident)'] = struct.unpack("<H", record[20:22])[0]
        dict['Attribute header size'] = 24
    elif dict['Resident'] == 1:
        dict['Resident (verbose)'] = '01 (Non resident content)'
        dict['Attribute header size'] = 16
    else:
        raise Exception("Wrong value for Resident flag - possible values (00, 01)")


########################## $STANDARD_INFORMATION ATTRIBUTE #############################################################

def parse_standard(standard, raw_record, next_offset):
    standard.clear()
    standard['Attribute first offset'] = next_offset
    if raw_record[next_offset:next_offset + 4] != b'\x10\x00\x00\x00':
        raise Exception("Wrong start of STANDARD_INFORMATION attribute")
    record = raw_record[next_offset:]

    parse_attribute_header(record, standard)
    if standard['Resident'] == 0:
        content_offset = standard['Content start offset (resident)']
    else:
        content_offset = standard['Content start offset']
    record = record[content_offset:]

    standard['Creation time'] = convert_filetime(struct.unpack("<Q", record[:8])[0])
    standard['Modification time'] = convert_filetime(struct.unpack("<Q", record[8:16])[0])
    standard['Entry modification time'] = convert_filetime(struct.unpack("<Q", record[16:24])[0])
    standard['Last accessed time'] = convert_filetime(struct.unpack("<Q", record[24:32])[0])
    f_type = struct.unpack("<I", record[32:36])[0]
    standard['File type'] = is_set(f_type, file_type)

    return standard


########################## $ATTRIBUTE_LIST ATTRIBUTE ###################################################################
def parse_attribute_list(attribute_list, raw_record, next_offset):
    attribute_list.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x20\x00\x00\x00':
        raise Exception("Wrong start of ATTRIBUTE_LIST attribute")

    record = raw_record[next_offset:]
    attribute_list['Attribute first offset'] = next_offset
    parse_attribute_header(record, attribute_list)
    return attribute_list


########################## $FILE_NAME ATTRIBUTE ########################################################################

def parse_filename(filename, raw_record, next_offset):
    filename.clear()
    filename['Attribute first offset'] = next_offset
    if raw_record[next_offset:next_offset + 4] != b'\x30\x00\x00\x00':
        raise Exception("Wrong start of FILE_NAME attribute")
    record = raw_record[next_offset:]

    parse_attribute_header(record, filename)

    if filename['Resident'] == 0:
        content_offset = filename['Content start offset (resident)']
    else:
        content_offset = filename['Content start offset']

    record = record[content_offset:]
    filename['Parent entry number'] = struct.unpack("<HHH", record[:6])[0]
    # timezone en UTC !
    filename['Creation time'] = convert_filetime(struct.unpack("<Q", record[8:16])[0])
    filename['Modification time'] = convert_filetime(struct.unpack("<Q", record[16:24])[0])
    filename['Entry modification time'] = convert_filetime(struct.unpack("<Q", record[24:32])[0])
    filename['Last accessed time'] = convert_filetime(struct.unpack("<Q", record[32:40])[0])
    filename['Filename length'] = struct.unpack("<B", record[64:65])[0] * 2
    length = filename['Filename length']
    filename['Filename'] = record[66:66 + length].decode('utf-16')

    return filename


########################## $OBJECT_ID ATTRIBUTE ########################################################################

def parse_objectid(object_id, raw_record, next_offset):
    object_id.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x40\x00\x00\x00':
        raise Exception("Wrong start of OBJECT_ID attribute")

    record = raw_record[next_offset:]
    object_id['Attribute first offset'] = next_offset
    parse_attribute_header(record, object_id)
    return object_id


########################## $SECURITY_DESCRIPTOR ATTRIBUTE ##############################################################

def parse_security_descriptor(security_descriptor, raw_record, next_offset):
    security_descriptor.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x50\x00\x00\x00':
        raise Exception("Wrong start of SECURITY_DESCRIPTOR attribute")

    record = raw_record[next_offset:]
    security_descriptor['Attribute first offset'] = next_offset
    parse_attribute_header(record, security_descriptor)
    return security_descriptor


########################## $SVOLUME_NAME ATTRIBUTE #####################################################################

def parse_volume_name(volume_name, raw_record, next_offset):
    volume_name.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x60\x00\x00\x00':
        raise Exception("Wrong start of VOLUME_NAME attribute")
    else:
        record = raw_record[next_offset:]
        volume_name['Attribute first offset'] = next_offset
        parse_attribute_header(record, volume_name)
        return volume_name


########################## $VOLUME_INFORMATION ATTRIBUTE ###############################################################

# TODO: parser le contenu du $VOLUME_INFORMATION
def parse_volume_information(volume_information, raw_record, next_offset):
    volume_information.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x70\x00\x00\x00':
        raise Exception("Wrong start of VOLUME_INFORMATION attribute")
    else:
        record = raw_record[next_offset:]
        volume_information['Attribute first offset'] = next_offset
        parse_attribute_header(record, volume_information)
        return volume_information


########################## $DATA ATTRIBUTE #############################################################################

def parse_data(data, raw_record, offset, k):
    data.clear()

    if raw_record[offset:offset + 4] != b'\x80\x00\x00\x00':
        # raise Exception(f"Wrong start of DATA attribute at entry {k}")
        print(f'There was a problem at entry {k} with the DATA attribute')
        return None
    record = raw_record[offset:]

    data['Attribute first offset'] = offset
    parse_attribute_header(record, data)

    content_offset = data['Attribute header size']
    record = record[content_offset:]
    if data['Resident'] == 1:
        data['Run list\'s virtual first cluster number'] = struct.unpack("<Q", record[0:8])[0]
        data['Run list\'s virtual last cluster number'] = struct.unpack("<Q", record[8:16])[0]
        data['Run list\'s start offset'] = struct.unpack("<H", record[16:18])[0]
        data['File physical size'] = struct.unpack("<Q", record[24:32])[0]
        data['File logical size'] = struct.unpack("<Q", record[32:40])[0]
        data['File initialized size'] = struct.unpack("<Q", record[40:48])[0]

        # left nibble = number of bytes that contains the position of the cluster in the pointer
        # right nibble = number of bytes that contains the number of cluster in the pointer
        first_off = data['Run list\'s start offset'] - 16
        pointer_length = struct.unpack("<B", record[first_off:first_off + 1])[0]
        left, right = pointer_length >> 4, pointer_length & 0x0F
        first_off += 1

        # run list made of tuples : (position of clusters, number of clusters)
        run_list = []
        i = 0
        while i < 4:
            nb_cluster = int.from_bytes(record[first_off:first_off + right], 'little')
            pos_cluster = int.from_bytes(record[first_off + right:first_off + left + right], 'little')
            first_off += (left + right)
            run_list.append((pos_cluster, nb_cluster))
            i += 1
            if record[first_off:first_off + 1] == b'\x00':
                break

        data['Run list'] = run_list

    elif data['Resident'] == 0:
        pass
    else:
        raise Exception("Wrong value for 'resident' - possible values (0,1)")

    return data


########################## $INDEX_ROOT ATTRIBUTE #######################################################################
# TODO: parser le contenu comme donne des infos sur le contenu du répertoire
def parse_index_root(index_root, raw_record, next_offset):
    index_root.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x90\x00\x00\x00':
        raise Exception("Wrong start of INDEX_ROOT attribute")

    record = raw_record[next_offset:]
    index_root['Attribute first offset'] = next_offset
    parse_attribute_header(record, index_root)
    return index_root


########################## $INDEX_ALLOCATION ATTRIBUTE ##############################################################

def parse_index_allocation(index_allocation, raw_record, next_offset):
    index_allocation.clear()

    if raw_record[next_offset:next_offset + 4] != b'\xA0\x00\x00\x00':
        raise Exception("Wrong start of INDEX_ALLOCATION attribute")

    record = raw_record[next_offset:]
    index_allocation['Attribute first offset'] = next_offset
    parse_attribute_header(record, index_allocation)
    return index_allocation


########################## $BITMAP ATTRIBUTE ###########################################################################

def parse_bitmap(bitmap, raw_record, next_offset):
    bitmap.clear()

    if raw_record[next_offset:next_offset + 4] != b'\xB0\x00\x00\x00':
        raise Exception("Wrong start of INDEX_ALLOCATION attribute")

    record = raw_record[next_offset:]
    bitmap['Attribute first offset'] = next_offset
    parse_attribute_header(record, bitmap)
    return bitmap


########################## $LOGGED_UTILITY_STREAM ATTRIBUTE ############################################################
# TODO: apparemment utilisé quand un fichier est chiffré, stocke la clé concernée
def parse_logged_utility_stream(logged_utility_stream, raw_record, next_offset):
    logged_utility_stream.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x00\x01\x00\x00':
        raise Exception("Wrong start of INDEX_ALLOCATION attribute")

    record = raw_record[next_offset:]
    logged_utility_stream['Attribute first offset'] = next_offset
    parse_attribute_header(record, logged_utility_stream)
    return logged_utility_stream


########################################################################################################################

MFT = {}


def parse_all(records_dict):
    n = 1

    for k, v in records_dict.items():
        printProgressBar(n, len(records_dict), stage='parsing records')
        n += 1

        MFT_record['header'] = parse_header(header, v)
        if MFT_record['header'] is None:
            pass
        else:
            next_offset = header['First attribute offset']
            while v[next_offset:next_offset+4] != b'\xFF\xFF\xFF\xFF':
                if v[next_offset:next_offset + 4] == b'\x10\x00\x00\x00':
                    MFT_record['$STANDARD_INFORMATION'] = parse_standard(standard, v, next_offset)
                    next_offset = MFT_record['$STANDARD_INFORMATION']['Attribute first offset'] + \
                                  MFT_record['$STANDARD_INFORMATION']['Attribute size']

                if v[next_offset:next_offset + 4] == b'\x20\x00\x00\x00':
                    MFT_record['$ATTRIBUTE_LIST'] = parse_attribute_list(attribute_list, v, next_offset)
                    next_offset = MFT_record['$ATTRIBUTE_LIST']['Attribute first offset'] + \
                                  MFT_record['$ATTRIBUTE_LIST']['Attribute size']

                while True:
                    if v[next_offset:next_offset + 4] == b'\x30\x00\x00\x00':
                        MFT_record['$FILE_NAME'] = parse_filename(filename, v, next_offset)
                        next_offset = MFT_record['$FILE_NAME']['Attribute first offset'] + MFT_record['$FILE_NAME'][
                            'Attribute size']

                        if v[next_offset:next_offset + 4] == b'\x30\x00\x00\x00':
                            filenames = []
                            filenames.append(filename['Filename'])
                            MFT_record['$FILE_NAME'] = parse_filename(filename, v, next_offset)
                            next_offset = MFT_record['$FILE_NAME']['Attribute first offset'] + MFT_record['$FILE_NAME'][
                                'Attribute size']
                            filenames.append(filename['Filename'])
                            MFT_record['$FILE_NAME']['Filename'] = filenames
                    else:
                        break

                if v[next_offset:next_offset + 4] == b'\x40\x00\x00\x00':
                    MFT_record['$OBJECT_ID'] = parse_objectid(object_id, v, next_offset)
                    next_offset = MFT_record['$OBJECT_ID']['Attribute first offset'] + \
                                  MFT_record['$OBJECT_ID']['Attribute size']

                if v[next_offset:next_offset + 4] == b'\x50\x00\x00\x00':
                    MFT_record['$SECURITY_DESCRIPTOR'] = parse_security_descriptor(security_descriptor, v, next_offset)
                    next_offset = MFT_record['$SECURITY_DESCRIPTOR']['Attribute first offset'] + \
                                  MFT_record['$SECURITY_DESCRIPTOR']['Attribute size']

                if v[next_offset:next_offset + 4] == b'\x60\x00\x00\x00':
                    MFT_record['$VOLUME_NAME'] = parse_volume_name(volume_name, v, next_offset)
                    next_offset = MFT_record['$VOLUME_NAME']['Attribute first offset'] + \
                                  MFT_record['$VOLUME_NAME']['Attribute size']

                if v[next_offset:next_offset + 4] == b'\x70\x00\x00\x00':
                    MFT_record['$VOLUME_INFORMATION'] = parse_volume_information(volume_information, v, next_offset)
                    next_offset = MFT_record['$VOLUME_INFORMATION']['Attribute first offset'] + \
                                  MFT_record['$VOLUME_INFORMATION']['Attribute size']

                datas =[]
                while True:
                    if v[next_offset:next_offset + 4] == b'\x80\x00\x00\x00':
                        MFT_record['$DATA'] = parse_data(data, v, next_offset, k)
                        next_offset = MFT_record['$DATA']['Attribute first offset'] + \
                                      MFT_record['$DATA']['Attribute size']

                        if v[next_offset:next_offset + 4] == b'\x80\x00\x00\x00':
                            if data['Resident'] == 1:
                                datas.append(data['Run list'])
                            MFT_record['$DATA'] = parse_data(data, v, next_offset, k)
                            next_offset = MFT_record['$DATA']['Attribute first offset'] + MFT_record['$DATA'][
                                'Attribute size']

                            if data['Resident'] == 1 and len(datas) != 0:
                                datas.append(data['Run list'])
                                MFT_record['$DATA']['Run list'] = datas
                    else:
                        break

                if v[next_offset:next_offset + 4] == b'\x90\x00\x00\x00':
                    MFT_record['$INDEX_ROOT'] = parse_index_root(index_root, v, next_offset)
                    next_offset = MFT_record['$INDEX_ROOT']['Attribute first offset'] + \
                                  MFT_record['$INDEX_ROOT']['Attribute size']

                if v[next_offset:next_offset + 4] == b'\xA0\x00\x00\x00':
                    MFT_record['$INDEX_ALLOCATION'] = parse_index_allocation(index_allocation, v, next_offset)
                    next_offset = MFT_record['$INDEX_ALLOCATION']['Attribute first offset'] + \
                                  MFT_record['$INDEX_ALLOCATION']['Attribute size']

                if v[next_offset:next_offset + 4] == b'\xB0\x00\x00\x00':
                    MFT_record['$BITMAP'] = parse_bitmap(bitmap, v, next_offset)
                    next_offset = MFT_record['$BITMAP']['Attribute first offset'] + \
                                  MFT_record['$BITMAP']['Attribute size']

                if v[next_offset:next_offset + 4] == b'\x00\x01\x00\x00':
                    MFT_record['$LOGGED_UTILITY_STREAM'] = parse_logged_utility_stream(logged_utility_stream, v,
                                                                                       next_offset)
                    next_offset = MFT_record['$LOGGED_UTILITY_STREAM']['Attribute first offset'] + \
                                  MFT_record['$LOGGED_UTILITY_STREAM']['Attribute size']

                #if v[next_offset:next_offset + 4] == b'\xFF\xFF\xFF\xFF':
            MFT[k] = copy.deepcopy(MFT_record)
                    #break

            MFT_record.clear()

    return MFT


if __name__ == '__main__':
    parser = ArgumentParser(description='MFT parser : parse MFT entries and return details of each attributes')
    parser.add_argument('-f', '--file', help='MFT file', required=True)
    parser.add_argument('-c', '--csv', help='output MFT content into a csv file', required=False)
    parser.add_argument('-j', '--json', help='output MFT content into a csv json', required=False)

    args = parser.parse_args()

    # TODO : un peu rustre d'ouvrir deux fois le fichier
    with open(args.file, 'rb') as f:
        length_MFT = len(f.read())
        print(f'Starting the parsing of the $MFT..')
        print(f'There is a total of {length_MFT // 1024} entries in the MFT')
        # 262144

    i = 0
    j = length_MFT // 1024
    mftRecords = {}
    with open(args.file, 'rb') as f:
        chunk = f.read(MFT_RECORD_SIZE)
        while i < j:
            try:
                mftRecords[i] = chunk
                chunk = f.read(MFT_RECORD_SIZE)
                i += 1
            except Exception:
                print(f'There was a problem at entry number {i}')
                break

    MFT_parsed = parse_all(mftRecords)
    print(f'The parsing has finished successfully \n{len(MFT_parsed)}/{length_MFT // 1024} used entries in the MFT')

    if args.json:
        MFT_to_json(MFT_parsed, args.json)

    if args.csv:
        print(f'Writting to a CSV file.. this operation may take some time')
        MFT_to_csv(MFT_parsed, args.csv)
        print(f'Process finished !')
