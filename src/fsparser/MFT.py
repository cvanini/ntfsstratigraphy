#### Céline Vanini
#### 02.03.2021

'''MFT parser : extract the entries attributes informations based on offset values.
Principal attributes that can be recovered are $STANDARD_INFORMATION, $FILE_NAME and $DATA.
For the other attributes, only the header is parsed (rest of info not necessary in this context).
Will be managed afterwards.

Sources : File system forensic analysis (B. Carrier, 2005) and https://flatcap.github.io/linux-ntfs/ntfs/attributes/index.html
'''
import sys
import os

sys.path.append(os.getcwd() + '\\src')

import copy
import struct
import logging
from fsparser.ressources.dict import *
from fsparser.ressources.utils import *
from fsparser.ressources.ProgressBar import printProgressBar
from argparse import ArgumentParser

MFT_RECORD_SIZE = 1024

MFT_logger = logging.getLogger('MFT')

MFT_record = {
    'header': '',
    '$STANDARD_INFORMATION': '',
    '$FILE_NAME': '',
    '$DATA': ''
}


# TODO: gérer les BAAD
# TODO: Gérer les non-base MFT entry (lorsque besoin de + d'une entrée pour stocker tous les attributs d'un fichier)
#  -> ils vont avoir un $ATTRIBUTE_LIST (0x20000000)
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
    # Equivalent to the header size:
    header['First attribute offset'] = struct.unpack("<H", raw_record[20:22])[0]
    # Status of the file
    header['Allocation flag'] = struct.unpack("<H", raw_record[22:24])[0]
    match header['Allocation flag']:
        case 0: header['Allocation flag (verbose)'] = '00 (Deleted file)'
        case 1: header['Allocation flag (verbose)'] = '01 (Visible file)'
        case 2: header['Allocation flag (verbose)'] = '02 (Deleted directory)'
        case 3: header['Allocation flag (verbose)'] = '03 (Visible directory)'
        case 4: header['Allocation flag (verbose)'] = '04 (Extension)'
        case 8: header['Allocation flag (verbose)'] = '08 (Special index)'
        case _: header['Allocation flag (verbose)'] = 'Unknown allocation flag'

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
    # This part gives the number of character of the name. As encoded in utf-16, multiplied by 2 to consider 2 bytes.
    dict['Attribute name length'] = struct.unpack("<B", record[9:10])[0]*2
    dict['Offset to name'] = struct.unpack("<H", record[10:12])[0]
    # File type
    dict['Flags'] = struct.unpack("<H", record[12:14])[0]

    match dict['Flags']:
        case 0: dict['Flags (verbose)'] = 'None'
        case 1: dict['Flags (verbose)'] = 'Compressed'
        case 16384: dict['Flags (verbose)'] = 'Encrypted'
        case 32768: dict['Flags (verbose)'] = 'Sparse'
        case _: dict['Flags (verbose)'] = 'Unknown'

    dict['Attribute ID'] = struct.unpack("<H", record[14:16])[0]
    match dict['Resident']:
        case 0:
            dict['Resident (verbose)'] = '00 (Resident content)'
            dict['Attribute content size'] = struct.unpack("<I", record[16:20])[0]
            offset = struct.unpack("<H", record[20:22])[0]
            match dict['Attribute name length']:
                case 0:
                    dict['Attribute content start'] = offset
                    dict['Attribute header size'] = 24
                case _:
                    dict['Attribute content start'] = offset
                    dict['Attribute header size'] = 24 + dict['Attribute name length']
        case 1:
            dict['Resident (verbose)'] = '01 (Non resident content)'
            dict['Initial VCN'] = struct.unpack("<Q", record[16:24])[0]
            dict['Last VCN'] = struct.unpack("<Q", record[24:32])[0]
            match dict['Attribute name length']:
                case 0:
                    dict['Attribute header size'] = 16
                    dict['Run list\'s start offset'] = struct.unpack("<H", record[32:34])[0]
                case _:
                    dict['Attribute header size'] = 16 + dict['Attribute name length']
                    dict['Run list\'s start offset'] = struct.unpack("<H", record[32:34])[0] + dict['Attribute name length']
            dict['File physical size'] = struct.unpack("<Q", record[40:48])[0]
            dict['File logical size'] = struct.unpack("<Q", record[48:56])[0]
            dict['File initialized size'] = struct.unpack("<Q", record[56:64])[0]

        case _: raise Exception("Wrong value for Resident flag - possible values (00, 01)")

    # Useful for directories, that have a name in the header attribute ($I30)
    if dict['Attribute name length'] != 0:
        offset = dict['Offset to name']
        dict['Name'] = record[offset:offset+dict['Attribute name length']].decode('utf-16')

        match dict['Name']:
            # Index of filenames
            case '$I30': dict['Index type'] = 'Directory'
            case '$SDH': dict['Index type'] = 'Security descriptors index'
            case '$SII': dict['Index type'] = 'Security Ids index'
            case '$O': dict['Index type'] = 'Object Ids or Owner Ids indexes'
            case '$Q': dict['Index type'] = 'Quotas index'
            case '$R': dict['Index type'] = 'Reparse Points index'
            case _: pass

########################## $STANDARD_INFORMATION ATTRIBUTE #############################################################

# The $STANDARD_INFORMATION attribute can have a size that fits between 48 bytes to 72 bytes.
# The USN is therefore not always attributed to files/directories
# This attribute is always resident
def parse_standard(standard, raw_record, next_offset):
    standard.clear()
    standard['Attribute first offset'] = next_offset
    if raw_record[next_offset:next_offset + 4] != b'\x10\x00\x00\x00':
        raise Exception("Wrong start of STANDARD_INFORMATION attribute")
    record = raw_record[next_offset:]

    parse_attribute_header(record, standard)
    content_offset = standard['Attribute content start']
    record = record[content_offset:]

    standard['Creation time'] = convert_filetime(struct.unpack("<Q", record[:8])[0])
    standard['Modification time'] = convert_filetime(struct.unpack("<Q", record[8:16])[0])
    standard['Entry modification time'] = convert_filetime(struct.unpack("<Q", record[16:24])[0])
    standard['Last accessed time'] = convert_filetime(struct.unpack("<Q", record[24:32])[0])
    f_type = struct.unpack("<I", record[32:36])[0]
    standard['File type'] = is_set(f_type, file_type)
    # Maximum allowed versions for file (0 means version numbering is disabled)
    standard['Maximum number of versions'] = struct.unpack("<I", record[36:40])[0]
    standard['Version number'] = struct.unpack("<I", record[40:44])[0]
    standard['Class ID'] = struct.unpack("<I", record[44:48])[0]

    if standard['Attribute size'] == 72:
        # User owning the file
        standard['Owner ID'] = struct.unpack("<I", record[48:52])[0]
        # Not the SID, but a key for the SII Index in $Secure
        standard['Security ID'] = struct.unpack("<I", record[52:56])[0]
        # size of all streams
        standard['Quota charged'] = struct.unpack("<Q", record[56:64])[0]
        # Last update sequence number, direct index into the $UsnJrnl
        standard['Update Sequence Number (USN)'] = struct.unpack("<Q", record[64:72])[0]

    return standard


########################## $ATTRIBUTE_LIST ATTRIBUTE ###################################################################

# This attribute appears when there are too much attributes to store for an MFT entry. Attributes are listed
# and stored in this attribute.
def parse_attribute_list(attribute_list, raw_record, next_offset):
    attribute_list.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x20\x00\x00\x00':
        raise Exception("Wrong start of ATTRIBUTE_LIST attribute")

    record = raw_record[next_offset:]
    attribute_list['Attribute first offset'] = next_offset
    parse_attribute_header(record, attribute_list)

    # content_offset = attribute_list['Attribute content start']
    # record = record[content_offset:]

    return attribute_list


########################## $FILE_NAME ATTRIBUTE ########################################################################

def parse_filename(filename, raw_record, next_offset):
    filename.clear()
    filename['Attribute first offset'] = next_offset
    if raw_record[next_offset:next_offset + 4] != b'\x30\x00\x00\x00':
        raise Exception("Wrong start of FILE_NAME attribute")
    record = raw_record[next_offset:]

    parse_attribute_header(record, filename)

    content_offset = filename['Attribute content start']

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

# Way too complicate :)
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

def run_list(first_off, record):

    run_list = []
    # left nibble = number of bytes that contains the position of the cluster in the pointer
    # right nibble = number of bytes that contains the number of cluster in the pointer
    while True:
        pointer_length = struct.unpack("<B", record[first_off:first_off + 1])[0]
        left, right = pointer_length >> 4, pointer_length & 0x0F
        length = left + right
        first_off += 1

        nb_cluster = int.from_bytes(record[first_off:first_off + right], 'little')
        pos_cluster = int.from_bytes(record[first_off + right:first_off + length], 'little')
        first_off += length
        run_list.append((pos_cluster, nb_cluster))

        if record[first_off:first_off + 1] == b'\x00':
            break
    print(run_list)
    return run_list


def parse_data(data, raw_record, offset, k):
    data.clear()

    if raw_record[offset:offset + 4] != b'\x80\x00\x00\x00':
        # raise Exception(f"Wrong start of DATA attribute at entry {k}")
        print(f'There was a problem at entry {k} with the DATA attribute')
        return None
    record = raw_record[offset:]

    data['Attribute first offset'] = offset
    parse_attribute_header(record, data)

    # Note: doesn't extract the content of resident files
    if data['Resident'] == 1:
        first_off = data['Run list\'s start offset']
        # run list made of tuples : (position of clusters, number of clusters)
        data['Run list'] = run_list(first_off, record)


    return data

########################## $INDEX NODE HEADER ##########################################################################

def parse_index_node_header(index_node, record):
    index_node.clear()

    index_node['Offset for 1st entry (starting node header)'] = struct.unpack('<I', record[0:4])[0]
    index_node['Index entry total size'] = struct.unpack('<I', record[4:8])[0]
    index_node['Index entry allocated size'] = struct.unpack('<I', record[8:12])[0]
    index_node['Index flag'] = struct.unpack('<B', record[12:13])[0]

    match index_node['Index flag']:
        case 0: index_node['Index flag (verbose)'] = 'Small index (fits in $INDEX_ROOT)'
        case 1: index_node['Index flag (verbose)'] = 'Large index (external allocation needed)'
        case _: raise ValueError("Wrong flag value (only 0 or 1)")

    return index_node

########################## $INDEX ENTRY ################################################################################

# Only for directory indexes for now
def parse_index_entry(index_entry, index, record):
    index_entry.clear()
    # The stream is a copy of the filename content in the MFT entry of the indexed file/sub-directory
    index['Filenames in directory'] = []
    length_stream = index['Index entry allocated size'] - 16
    match index['Index flag']:
        case 0:
            while length_stream > 0:
                try:
                    #TODO: attention HHH ou Q ?
                    index_entry['MFT file reference'] = struct.unpack('<HHH', record[0:6])[0]
                    index_entry['Length of entry'] = struct.unpack('<H', record[8:10])[0]
                    index_entry['Length of stream'] = struct.unpack('<H', record[10:12])[0]
                    index_entry['Index entry flag'] = struct.unpack('<I', record[12:16])[0]

                    # Some entries may have only a header or a header + VCN (= no stream)
                    if index_entry['Length of stream'] != 0:
                        stream = record[16:]
                        filename_length = struct.unpack("<B", stream[64:65])[0] * 2
                        filename = stream[66:66 + filename_length].decode('utf-16')
                        if filename:
                            # TODO: gérer le cas où il y a 2 filenames
                            # The attribute contains a list of some of the childs that are present in the directory
                            # Each entry has a VCN and filename, telling NTFS that "at this VCN, I have all files starting
                            # after this letter, until next VCN"
                            index['Filenames in directory'].append(filename)
                    record = record[index_entry['Length of entry']:]
                    length_stream = length_stream-index_entry['Length of entry']

                    match index_entry['Index entry flag']:
                        case 1:
                            # VCN of child nodes (directories) in $INDEX_ALLOCATION attribute
                            index_entry['Index entry flag (verbose)'] = 'Child nodes exist'
                            entry = record[:index_entry['Length of entry']]
                            index_entry['VCN of child nodes'] = entry[:-8]
                        case 2:
                            index_entry['Index entry flag (verbose)'] = 'Last entry in list'
                            break
                        case 3:
                            # TODO: gérer les child nodes ?
                            index_entry['Index entry flag (verbose)'] = ['Child nodes exists', 'Last entry in list']
                            break
                        case _:
                            pass # index_entry['Index entry flag'])

                except Exception:
                    break

        case 1: pass

    return index
########################## $INDEX_ROOT ATTRIBUTE #######################################################################

# This attribute is always resident, always the root of the index tree and store a small list of index entries
# 16 bytes header, followed by a node header and a list of index entries
def parse_index_root(index_root, raw_record, next_offset):
    index_root.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x90\x00\x00\x00':
        raise Exception("Wrong start of INDEX_ROOT attribute")

    record = raw_record[next_offset:]
    index_root['Attribute first offset'] = next_offset
    parse_attribute_header(record, index_root)

    # Parsing the index root header
    start = index_root['Attribute content start']
    record = record[start:]
    index_root['Attribute type ID'] = struct.unpack('<I', record[0:4])[0]
    index_root['Type'] = attributes_ID[index_root['Attribute type ID']]
    index_root['Collation rule'] = struct.unpack('<I', record[4:8])[0]
    index_root['Index entry size'] = struct.unpack('<I', record[8:12])[0]
    # Number of clusters or logarithm of the size (given in the boot sector)
    index_root['Cluster per index record'] = struct.unpack('<B', record[12:13])[0]
    index_root.update(parse_index_node_header(index_node, record[16:]))

    # Parses only directory indexes for now
    if index_root['Type'] == '$FILE_NAME':
        match index_root['Index flag']:
            case 0: index_root.update(parse_index_entry(index_entry, index_root, record[32:]))
            case 1: pass
            case _: raise ValueError('Invalid flag value (0 or 1)')
    return index_root


########################## $INDEX_ALLOCATION ATTRIBUTE #################################################################

# This attribute is used when index entries cannot fit in the $INDEX_ROOT (Index flag = 1)
# One index entry = one node in the sorted tree
# This attribute is always non-resident, made of data runs then
def parse_index_allocation(index_allocation, raw_record, next_offset):
    index_allocation.clear()

    if raw_record[next_offset:next_offset + 4] != b'\xA0\x00\x00\x00':
        raise Exception("Wrong start of INDEX_ALLOCATION attribute")

    record = raw_record[next_offset:]
    index_allocation['Attribute first offset'] = next_offset
    parse_attribute_header(record, index_allocation)
    print(index_allocation)
    # The data run contains the cluster positions + numbers of the INDX - which is a list of index records describing
    # the names, length, etc. of files and directories contained in one parent directory. Its content is not considered
    # yet, as it is only the B-Tree that is used by NTFS to manage files and directories
    # The content of the following bitmap attribute tells which index record is in use.
    print(index_allocation['Run list\'s start offset'])
    index_allocation['Data run'] = run_list(index_allocation['Run list\'s start offset'], record)

    return index_allocation


########################## $BITMAP ATTRIBUTE ###########################################################################

# Not considered
def parse_bitmap(bitmap, raw_record, next_offset):
    bitmap.clear()

    if raw_record[next_offset:next_offset + 4] != b'\xB0\x00\x00\x00':
        raise Exception("Wrong start of INDEX_ALLOCATION attribute")

    record = raw_record[next_offset:]
    bitmap['Attribute first offset'] = next_offset
    parse_attribute_header(record, bitmap)
    return bitmap


########################## $LOGGED_UTILITY_STREAM ATTRIBUTE ############################################################

# Not considered
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

# Main function which parses the attributes one by one, if exists. As they are always written by order of attribute ID,
# the function only checks after the end of every structure, which is the attribute to parse next, or stops if it is
# the end of the entry.
def parse_all(records_dict):
    n = 1

    for k, v in records_dict.items():
        printProgressBar(n, len(records_dict), stage='parsing records [$MFT]')
        n += 1

        MFT_record['header'] = parse_header(header, v)
        if MFT_record['header'] is None:
            pass
        else:
            next_offset = header['First attribute offset']
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

                    # A file can have the two types of filename format (DOS and Win32)
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

            datas = []
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

                if v[next_offset:next_offset + 4] == b'\x90\x00\x00\x00':
                    MFT_record['$INDEX_ROOT'] = parse_index_root(index_root, v, next_offset)
                    next_offset = MFT_record['$INDEX_ROOT']['Attribute first offset'] + \
                                  MFT_record['$INDEX_ROOT']['Attribute size']
                    MFT[k] = copy.deepcopy(MFT_record)

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

            if v[next_offset:next_offset + 4] == b'\xFF\xFF\xFF\xFF':
                MFT[k] = copy.deepcopy(MFT_record)

            MFT_record.clear()

    return MFT

def main(path, k):
    with open(f"{path}\\{str(k)}\\$MFT", 'rb') as f:
        length_MFT = len(f.read())
        MFT_logger.info(f'There is a total of {length_MFT // 1024} entries in the MFT')
        # 262144

    i = 0
    j = length_MFT // 1024
    mftRecords = {}
    with open(f"{path}\\{str(k)}\\$MFT", 'rb') as f:
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
    # MFT_parsed_ = parse_tree(MFT_parsed)
    MFT_logger.info(f'The parsing has finished successfully. {len(MFT_parsed_)}/{length_MFT // 1024} used entries in the MFT')

    MFT_logger.info(f'Writting to a CSV file.. this operation may take some time')
    MFT_to_csv(MFT_parsed_, f"{path}\\MFT_{str(k)}.csv")
    MFT_logger.info(f'CSV file of the $MFT is written !')

def log(path, k):
    MFT_logger.info(f'Starting the parsing of the $MFT..')
    main(path, k)
    MFT_logger.info(f'Process finished !')


if __name__ == '__main__':
    parser = ArgumentParser(description='MFT parser : parse MFT entries and return details of each attributes')
    parser.add_argument('-f', '--file', help='MFT file', required=True)
    parser.add_argument('-c', '--csv', help='output MFT content into a csv file', required=False)
    parser.add_argument('-j', '--json', help='output MFT content into a csv json', required=False)

    args = parser.parse_args()

    with open(args.file, 'rb') as f:
        length_MFT = len(f.read())
        logging.info(f'Starting the parsing of the $MFT..')
        logging.info(f'There is a total of {length_MFT // 1024} entries in the MFT')

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
    MFT_parsed = parse_tree(MFT_parsed)
    logging.info(f'The parsing has finished successfully \n{len(MFT_parsed)}/{length_MFT // 1024} used entries in the MFT')

    if args.json:
        MFT_to_json(MFT_parsed, args.json)

    if args.csv:
        logging.info(f'Writting to a CSV file.. this operation may take some time')
        MFT_to_csv(MFT_parsed, args.csv)
        logging.info(f'CSV file of the $MFT is written !')
