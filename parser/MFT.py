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
import copy
import struct
import logging
from tqdm import tqdm
from parser.ressources.dict import *
from parser.ressources.MFT_utils import *
from parser.ressources.plot import *
from argparse import ArgumentParser

MFT_RECORD_SIZE = 1024

MFT_logger = logging.getLogger('MFT')

# sys.path.append(os.getcwd() + '\\src')

MFT_record = {
    'header': '',
    '$STANDARD_INFORMATION': '',
    '$FILE_NAME': '',
    '$DATA': ''
}


# TODO: gérer les BAAD
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
    header['Sequence number'] = struct.unpack("<H", raw_record[16:18])[0]
    # Link count = how many directories referencing this MFT entry
    # If hard links were created for the file, this number is incremented by one for each link.
    header['Hard link count'] = struct.unpack("<H", raw_record[18:20])[0]
    # Equivalent to the header size:
    header['First attribute offset'] = struct.unpack("<H", raw_record[20:22])[0]
    # Status of the file
    header['Allocation flag'] = struct.unpack("<H", raw_record[22:24])[0]
    match header['Allocation flag']:
        case 0:
            header['Allocation flag (verbose)'] = '00 (Deleted file)'
        case 1:
            header['Allocation flag (verbose)'] = '01 (Visible file)'
        case 2:
            header['Allocation flag (verbose)'] = '02 (Deleted directory)'
        case 3:
            header['Allocation flag (verbose)'] = '03 (Visible directory)'
        case 4:
            header['Allocation flag (verbose)'] = '04 (Extension)'
        case 8:
            header['Allocation flag (verbose)'] = '08 (Special index)'
        case _:
            header['Allocation flag (verbose)'] = 'Unknown allocation flag'

    header['Entry logical size'] = struct.unpack("<I", raw_record[24:28])[0]
    header['Entry physical size'] = struct.unpack("<I", raw_record[28:32])[0]
    # Used when multiple entries have to be used for one file : attributes are listed in $ATTRIBUTE_LIST in one
    # base entry and sub-entries contain in their header the MFT entry number of the base entry:
    header['Base record entry number'] = unpack6(raw_record[32:38])
    header['Base record sequence number'] = struct.unpack('<H', raw_record[38:40])[0]
    header['Base record reference'] = ''.join([str(x) for x in raw_record[32:40]])
    header['Next attribute ID'] = struct.unpack("<H", raw_record[40:42])[0]
    header['Entry number'] = struct.unpack("<I", raw_record[44:48])[0]

    MFT_record['header'] = header

    return header


def parse_attribute_header(record, dict):
    # includes the header ~of the header
    dict['Attribute size'] = struct.unpack("<I", record[4:8])[0]
    dict['Attribute size entry'] = struct.unpack("<H", record[4:6])[0]
    dict['Resident'] = struct.unpack("<B", record[8:9])[0]
    # This part gives the number of character of the name. As encoded in utf-16, multiplied by 2 to consider 2 bytes.
    dict['Attribute name length'] = struct.unpack("<B", record[9:10])[0] * 2
    dict['Offset to name'] = struct.unpack("<H", record[10:12])[0]
    # File type
    dict['Flags'] = struct.unpack("<H", record[12:14])[0]
    match dict['Flags']:
        case 0:
            dict['Flags (verbose)'] = 'None'
        case 1:
            dict['Flags (verbose)'] = 'Compressed'
        case 16384:
            dict['Flags (verbose)'] = 'Encrypted'
        case 32768:
            dict['Flags (verbose)'] = 'Sparse'
        case _:
            dict['Flags (verbose)'] = 'Unknown'

    dict['Attribute number in entry'] = struct.unpack("<H", record[14:16])[0]

    # 4 cases : attributes can be resident-have a name, resident-no name, non-resident-have a name, non-resident-no name
    # Content of the attribute/Run list do not start at the same offset depending the case
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
            dict['Run list\'s start offset'] = struct.unpack("<H", record[32:34])[0]

            match dict['Attribute name length']:
                case 0:
                    dict['Attribute header size'] = 16
                case _:
                    dict['Attribute header size'] = 16 + dict['Attribute name length']
            dict['File physical size'] = struct.unpack("<Q", record[40:48])[0]
            dict['File logical size'] = struct.unpack("<Q", record[48:56])[0]
            dict['File initialized size'] = struct.unpack("<Q", record[56:64])[0]

        case _:
            raise Exception("Wrong value for Resident flag - possible values (00, 01)")

    # Useful for directories, that have a name in the header attribute ($I30)
    if dict['Attribute name length'] != 0:
        offset = dict['Offset to name']
        dict['Name'] = record[offset:offset + dict['Attribute name length']].decode('utf-16')

        # Some of the referenced name in the litterature
        match dict['Name']:
            # Index of filenames
            case '$I30':
                dict['Index type'] = 'Directory'
            case '$SDH':
                dict['Index type'] = 'Security descriptors index'
            case '$SII':
                dict['Index type'] = 'Security Ids index'
            case '$O':
                dict['Index type'] = 'Object Ids or Owner Ids indexes'
            case '$Q':
                dict['Index type'] = 'Quotas index'
            case '$R':
                dict['Index type'] = 'Reparse Points index'
            case _:
                pass


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

    # Use the function convert_filetime from the module MFT_utils.py
    standard['Creation time'] = convert_filetime(struct.unpack("<Q", record[:8])[0])
    standard['Modification time'] = convert_filetime(struct.unpack("<Q", record[8:16])[0])
    standard['Entry modification time'] = convert_filetime(struct.unpack("<Q", record[16:24])[0])
    standard['Last accessed time'] = convert_filetime(struct.unpack("<Q", record[24:32])[0])
    # The function is_set is used to extract the bits set to 1 in the binary form of this hex value
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

    next = standard['Attribute size entry'] + standard['Attribute first offset']

    return standard, next


########################## $ATTRIBUTE_LIST ATTRIBUTE ###################################################################

# This attribute appears when there are too much attributes to store for an MFT entry. Attributes are listed
# and stored in this attribute. Can be either resident or non-resident
# The list is sorted by : 1. attribute type 2. Attribute name (if present) 3. Sequence number
def parse_attribute_list(attribute_list, raw_record, next_offset):
    attribute_list.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x20\x00\x00\x00':
        raise Exception("Wrong start of ATTRIBUTE_LIST attribute")

    record = raw_record[next_offset:]
    attribute_list['Attribute first offset'] = next_offset
    parse_attribute_header(record, attribute_list)

    match attribute_list['Resident']:
        case 0:
            content_offset = attribute_list['Attribute content start']
            record = record[content_offset:]
            # TODO: change here?
            length = attribute_list['Attribute size'] - attribute_list['Attribute header size']

            attributes = {}
            while length > 0:
                type = attributes_ID[struct.unpack('<I', record[0:4])[0]]
                record_length = struct.unpack('<H', record[4:6])[0]
                base_file_reference = unpack6(record[16:22])
                attributes[type] = base_file_reference

                length = length - record_length
                record = record[record_length:]
            attribute_list['List'] = attributes
        # content of the attribute list may not be resident if too much $FILE_NAME attributes are stored
        case 1:
            attribute_list['Data run'] = run_list(attribute_list['Run list\'s start offset'], record)

    next = attribute_list['Attribute size entry'] + attribute_list['Attribute first offset']

    return attribute_list, next


########################## $FILE_NAME ATTRIBUTE ########################################################################

# This attribute is always resident
def parse_filename(filename, raw_record, next_offset):
    filename.clear()
    filename['Attribute first offset'] = next_offset
    if raw_record[next_offset:next_offset + 4] != b'\x30\x00\x00\x00':
        raise Exception("Wrong start of FILE_NAME attribute")
    record = raw_record[next_offset:]

    parse_attribute_header(record, filename)

    content_offset = filename['Attribute content start']

    record = record[content_offset:]
    # On 8 bytes normally, the last 2 concern the sequence number of the parent entry
    filename['Parent entry number'] = unpack6(record[:6])
    filename['Parent entry sequence number'] = struct.unpack('<H', record[6:8])[0]
    # timezone en UTC !
    filename['Creation time'] = convert_filetime(struct.unpack("<Q", record[8:16])[0])
    filename['Modification time'] = convert_filetime(struct.unpack("<Q", record[16:24])[0])
    filename['Entry modification time'] = convert_filetime(struct.unpack("<Q", record[24:32])[0])
    filename['Last accessed time'] = convert_filetime(struct.unpack("<Q", record[32:40])[0])
    filename['Allocated size of file'] = struct.unpack('<Q', record[40:48])[0]
    filename['Actual size of file'] = struct.unpack('<Q', record[48:56])[0]
    filename['Filename length'] = struct.unpack("<B", record[64:65])[0] * 2
    length = filename['Filename length']
    filename['Filename'] = record[66:66 + length].decode('utf-16')

    next = filename['Attribute size entry'] + filename['Attribute first offset']

    return filename, next


########################## $OBJECT_ID ATTRIBUTE ########################################################################

# Not used
def parse_objectid(object_id, raw_record, next_offset):
    object_id.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x40\x00\x00\x00':
        raise Exception("Wrong start of OBJECT_ID attribute")

    record = raw_record[next_offset:]
    object_id['Attribute first offset'] = next_offset
    parse_attribute_header(record, object_id)

    next = object_id['Attribute size entry'] + object_id['Attribute first offset']

    return object_id, next


########################## $SECURITY_DESCRIPTOR ATTRIBUTE ##############################################################

# Not used, but apparently stores encryption keys of files
def parse_security_descriptor(security_descriptor, raw_record, next_offset):
    security_descriptor.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x50\x00\x00\x00':
        raise Exception("Wrong start of SECURITY_DESCRIPTOR attribute")

    record = raw_record[next_offset:]
    security_descriptor['Attribute first offset'] = next_offset
    parse_attribute_header(record, security_descriptor)

    next = security_descriptor['Attribute size entry'] + security_descriptor['Attribute first offset']

    return security_descriptor, next


########################## $SVOLUME_NAME ATTRIBUTE #####################################################################

# Not used
def parse_volume_name(volume_name, raw_record, next_offset):
    volume_name.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x60\x00\x00\x00':
        raise Exception("Wrong start of VOLUME_NAME attribute")

    record = raw_record[next_offset:]
    volume_name['Attribute first offset'] = next_offset
    parse_attribute_header(record, volume_name)
    next = volume_name['Attribute size entry'] + volume_name['Attribute first offset']

    return volume_name, next


########################## $VOLUME_INFORMATION ATTRIBUTE ###############################################################

# Not used
def parse_volume_information(volume_information, raw_record, next_offset):
    volume_information.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x70\x00\x00\x00':
        raise Exception("Wrong start of VOLUME_INFORMATION attribute")

    record = raw_record[next_offset:]
    volume_information['Attribute first offset'] = next_offset
    parse_attribute_header(record, volume_information)

    next = volume_information['Attribute size entry'] + volume_information['Attribute first offset']

    return volume_information, next


########################## $DATA ATTRIBUTE #############################################################################

def run_list(first_off, record):
    # left nibble = number of bytes that contains the position of the cluster in the pointer
    # right nibble = number of bytes that contains the number of cluster in the pointer
    run_list = []
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

    return run_list, run_list[0][0]


def parse_data(data, raw_record, offset):
    data.clear()

    if raw_record[offset:offset + 4] != b'\x80\x00\x00\x00':
        # raise Exception(f"Wrong start of DATA attribute at entry {k}")
        print(f'There was a problem with the DATA attribute')
        return None
    record = raw_record[offset:]

    data['Attribute first offset'] = offset
    parse_attribute_header(record, data)

    # Note: doesn't extract the content of resident files
    if data['Resident'] == 1:
        first_off = data['Run list\'s start offset']
        # run list made of tuples : (position of clusters, number of clusters)
        data['Run list'], data['First cluster'] = run_list(first_off, record)

    next = data['Attribute size entry'] + data['Attribute first offset']

    return data, next


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
    # Attribute type ID = 0 if index entry doesn't use an attribute
    # TODO: attention ?
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
            case 0:
                index_root.update(parse_index_entry(index_entry, index_root, record[32:]))
            case 1:
                pass
            case _:
                raise ValueError('Invalid flag value (0 or 1)')

    next = index_root['Attribute size entry'] + index_root['Attribute first offset']

    return index_root, next


########################## $INDEX NODE HEADER ##########################################################################

# This header is the root of the B-Tree
def parse_index_node_header(index_node, record):
    index_node.clear()

    index_node['Offset for 1st entry (starting node header)'] = struct.unpack('<I', record[0:4])[0]
    index_node['Index entry total size'] = struct.unpack('<I', record[4:8])[0]
    index_node['Index entry allocated size'] = struct.unpack('<I', record[8:12])[0]
    index_node['Index flag'] = struct.unpack('<B', record[12:13])[0]

    match index_node['Index flag']:
        case 0:
            index_node['Index flag (verbose)'] = 'Small index (fits in $INDEX_ROOT)'
        case 1:
            index_node['Index flag (verbose)'] = 'Large index (external allocation needed)'
        case _:
            raise ValueError("Wrong flag value (only 0 or 1)")

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
                    # The file reference is on 8 bytes : 6 for the MFT entry number and the last 2 for the sequence number
                    index_entry['MFT file reference'] = (unpack6(record[0:6]), struct.unpack('<H', record[6:8]))
                    index_entry['Length of entry'] = struct.unpack('<H', record[8:10])[0]
                    index_entry['Length of stream'] = struct.unpack('<H', record[10:12])[0]
                    index_entry['Index entry flag'] = struct.unpack('<I', record[12:16])[0]

                    # Some entries may have only a header or a header + VCN (= no stream)
                    if index_entry['Length of stream'] != 0:
                        stream = record[16:]
                        filename_length = struct.unpack("<B", stream[64:65])[0] * 2
                        filename = stream[66:66 + filename_length].decode('utf-16')
                        if filename:
                            # The attribute contains a list of some of the childs that are present in the directory
                            # Each entry has a VCN and filename, telling NTFS that "at this VCN, I have all files starting
                            # after this letter, until next VCN"
                            index['Filenames in directory'].append(filename)
                    record = record[index_entry['Length of entry']:]

                    length_stream = length_stream - index_entry['Length of entry']

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
                            pass  # index_entry['Index entry flag'])

                except Exception:
                    break

        case 1:
            pass

    return index


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
    # The data run contains the cluster positions + numbers of the INDX - which is a list of index records describing
    # the names, length, etc. of files and directories contained in one parent directory. Its content is not considered
    # yet, as it is only the B-Tree that is used by NTFS to manage files and directories
    # The content of the following bitmap attribute tells which index record is in use.
    # TODO : limiter aux I30 ? Prend aussi les security descriptor, etc.
    index_allocation['Data run'], index_allocation['First cluster'] = run_list(
        index_allocation['Run list\'s start offset'], record)
    next = index_allocation['Attribute size entry'] + index_allocation['Attribute first offset']

    return index_allocation, next


########################## $BITMAP ATTRIBUTE ###########################################################################

# Not considered
def parse_bitmap(bitmap, raw_record, next_offset):
    bitmap.clear()

    if raw_record[next_offset:next_offset + 4] != b'\xB0\x00\x00\x00':
        raise Exception("Wrong start of BITMAP attribute")

    record = raw_record[next_offset:]
    bitmap['Attribute first offset'] = next_offset
    parse_attribute_header(record, bitmap)

    next = bitmap['Attribute size entry'] + bitmap['Attribute first offset']

    return bitmap, next


########################## $REPARSE_POINT ATTRIBUTE ####################################################################

# Not considered
def parse_reparse_point(reparse_point, raw_record, next_offset):
    reparse_point.clear()

    if raw_record[next_offset:next_offset + 4] != b'\xC0\x00\x00\x00':
        raise Exception("Wrong start of $REPARSE_POINT attribute")

    record = raw_record[next_offset:]
    reparse_point['Attribute first offset'] = next_offset
    parse_attribute_header(record, reparse_point)
    next = reparse_point['Attribute size entry'] + reparse_point['Attribute first offset']

    return reparse_point, next


########################## $EA_INFORMATION_ ATTRIBUTE ##################################################################

# Not considered
def parse_ea_information(ea_information, raw_record, next_offset):
    ea_information.clear()

    if raw_record[next_offset:next_offset + 4] != b'\xD0\x00\x00\x00':
        raise Exception("Wrong start of $EA_INFORMATION attribute")

    record = raw_record[next_offset:]
    ea_information['Attribute first offset'] = next_offset
    parse_attribute_header(record, ea_information)

    next = ea_information['Attribute size entry'] + ea_information['Attribute first offset']

    return ea_information, next


########################## $EA ATTRIBUTE ###############################################################################

# Not considered
def parse_ea(ea, raw_record, next_offset):
    ea.clear()

    if raw_record[next_offset:next_offset + 4] != b'\xE0\x00\x00\x00':
        raise Exception("Wrong start of EA attribute")

    record = raw_record[next_offset:]
    ea['Attribute first offset'] = next_offset
    parse_attribute_header(record, ea)
    next = ea['Attribute size entry'] + ea['Attribute first offset']

    return ea, next


########################## $LOGGED_UTILITY_STREAM ATTRIBUTE ############################################################

# Not considered
def parse_logged_utility_stream(logged_utility_stream, raw_record, next_offset):
    logged_utility_stream.clear()

    if raw_record[next_offset:next_offset + 4] != b'\x00\x01\x00\x00':
        raise Exception("Wrong start of LOGGED_UTILITY_STREAM attribute")

    record = raw_record[next_offset:]
    logged_utility_stream['Attribute first offset'] = next_offset
    parse_attribute_header(record, logged_utility_stream)
    next = logged_utility_stream['Attribute size entry'] + logged_utility_stream['Attribute first offset']

    return logged_utility_stream, next


########################################################################################################################

MFT = {}


# Main function which parses the attributes one by one, if exists. As they are always written by order of attribute ID,
# the function only checks after the end of every structure, which is the attribute to parse next, or stops if it is
# the end of the entry.
def parse_attributes(records_dict):
    # tqdm module is used to print progress bar
    for k, v in tqdm(records_dict.items(), desc='[MFT]'):

        MFT_record['header'] = parse_header(header, v)
        if MFT_record['header'] is None:
            pass
        else:
            next_offset = header['First attribute offset']
            i, j = 1, 1
            while True:
                match v[next_offset:next_offset + 4]:
                    case b'\x10\x00\x00\x00':
                        MFT_record['$STANDARD_INFORMATION'], next_offset = parse_standard(standard, v, next_offset)
                    case b'\x20\x00\x00\x00':
                        MFT_record['$ATTRIBUTE_LIST'], next_offset = parse_attribute_list(attribute_list, v,
                                                                                          next_offset)
                    case b'\x30\x00\x00\x00':
                        # A file can have the two types of filename format (DOS and Win32)
                        if i == 1:
                            MFT_record['$FILE_NAME'], next_offset = parse_filename(filename, v, next_offset)
                        else:
                            f = {}
                            MFT_record[f'$FILE_NAME{str(i)}'], next_offset = parse_filename(f, v, next_offset)
                        i += 1
                    case b'\x40\x00\x00\x00':
                        MFT_record['$OBJECT_ID'], next_offset = parse_objectid(object_id, v, next_offset)
                    case b'\x50\x00\x00\x00':
                        MFT_record['$SECURITY_DESCRIPTOR'], next_offset = parse_security_descriptor(security_descriptor,
                                                                                                    v, next_offset)
                    case b'\x60\x00\x00\x00':
                        MFT_record['$VOLUME_NAME'], next_offset = parse_volume_name(volume_name, v, next_offset)
                    case b'\x70\x00\x00\x00':
                        MFT_record['$VOLUME_INFORMATION'], next_offset = parse_volume_information(volume_information, v,
                                                                                                  next_offset)
                    case b'\x80\x00\x00\x00':
                        if j == 1:
                            MFT_record['$DATA'], next_offset = parse_data(data, v, next_offset)
                        else:
                            d = {}
                            MFT_record[f'ADS{str(j - 1)}'], next_offset = parse_data(d, v, next_offset)
                        j += 1
                    case b'\x90\x00\x00\x00':
                        MFT_record['$INDEX_ROOT'], next_offset = parse_index_root(index_root, v, next_offset)
                    case b'\xA0\x00\x00\x00':
                        MFT_record['$INDEX_ALLOCATION'], next_offset = parse_index_allocation(index_allocation, v,
                                                                                              next_offset)
                    case b'\xB0\x00\x00\x00':
                        MFT_record['$BITMAP'], next_offset = parse_bitmap(bitmap, v, next_offset)
                    case b'\xC0\x00\x00\x00':
                        MFT_record['$REPARSE_POINT'], next_offset = parse_reparse_point(reparse_point, v, next_offset)
                    case b'\xD0\x00\x00\x00':
                        MFT_record['$EA_INFORMATION'], next_offset = parse_ea_information(ea_information, v,
                                                                                          next_offset)
                    case b'\xE0\x00\x00\x00':
                        MFT_record['$EA'], next_offset = parse_ea(ea, v, next_offset)
                    case b'\x00\x01\x00\x00':
                        MFT_record['$LOGGED_UTILITY_STREAM'], next_offset = parse_logged_utility_stream(
                            logged_utility_stream, v, next_offset)
                    case b'\xFF\xFF\xFF\xFF':
                        MFT[k] = copy.deepcopy(MFT_record)
                        break

            MFT_record.clear()

    return MFT


def parse_MFT(path):
    MFT_logger.info(f'Starting the parsing of the $MFT..')

    i = 0
    j = os.path.getsize(path) // 1024
    MFT_logger.info(f'There is a total of {j} entries in the MFT')

    mftRecords = {}
    with open(path, 'rb') as f:
        chunk = f.read(MFT_RECORD_SIZE)
        while i < j:
            try:
                mftRecords[i] = chunk
                chunk = f.read(MFT_RECORD_SIZE)
                i += 1
            except Exception:
                print(f'There was a problem at entry number {i}')
                break

    MFT_parsed = parse_attributes(mftRecords)
    MFT_parsed = parse_tree(MFT_parsed)
    MFT_logger.info(f'The parsing has finished successfully. {len(MFT_parsed)}/{j} used entries in the MFT')

    return MFT_parsed


if __name__ == '__main__':
    parser = ArgumentParser(description='MFT parser : parse MFT entries and return details of each attributes')
    parser.add_argument('-f', '--file', help='MFT file', required=True)
    parser.add_argument('-o', '--output', help='output directory for the created files', required=True)
    parser.add_argument('-c', '--csv', help='output MFT content into a csv file', required=False, action='store_true')
    parser.add_argument('-j', '--json', help='output MFT content into a csv json', required=False, action='store_true')


    args = parser.parse_args()

    if not os.path.isdir(args.output):
        os.mkdir(args.output)

    logging.basicConfig(format='%(asctime)s - %(name)-12s: %(message)s',
                        datefmt='[%d.%m.%Y %H:%M:%S]', level=logging.INFO,
                        handlers=[logging.FileHandler(f'{args.output}\\MFT.txt'), logging.StreamHandler()])

    i = 0
    j = os.path.getsize(args.file) // 1024
    logging.info(f'Starting the parsing of the $MFT..')
    logging.info(f'There is a total of {j} entries in the MFT')

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

    MFT_parsed = parse_attributes(mftRecords)
    MFT_parsed = parse_tree(MFT_parsed)
    logging.info(
        f'The parsing has finished successfully \n{len(MFT_parsed)}/{j} used entries in the MFT')

    if args.json:
        MFT_to_json(args.output, MFT_parsed)

    if args.csv:
        MFT_to_csv(args.output, MFT_parsed)
