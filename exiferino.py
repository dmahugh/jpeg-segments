"""Extract Exif and related metadata from a JPEG file.

Functions:
exifdata_tostring -> convert Exif value to displayable string
read_app0_jfif ----> read JFIF metadata from an APP0 segment
read_app1_exif ----> read Exif metadata from an APP1 segment
read_app1_xmp -----> read XMP metadata from an APP1 segment
read_app1_xmpext --> read XMP Extended metadata from an APP1 segment
read_app12 --------> read metadata from APP12 segment
read_app13 --------> read metadata from APP13 segment
read_ifd ----------> read an IFD structure (Image File Directory)
readmeta ----------> generate a dictionary of metadata for a Jpeg file
readmeta_print ----> prints a dictionary returned by readmeta()
segment_map -------> generate a list of all segments in a Jpeg file
verify_exifheader -> verify the 6-byte Exif header
verify_jfifheader -> verify the 5-byte Exif header
verify_marker -----> verify a 2-byte segment marker in the Jpeg file
verify_tiffheader -> verify the 8-byte TIFF header
xmpns_tagtype -----> convert an XMP namespace to tagtype identifier

Classes:
ExifDecoder -------> Decode byte strings from a Jpeg/Exif file
"""
import re
import struct
import sys
from collections import deque
from xml.etree.ElementTree import fromstring
from jpegdata import exiftag, seginfo, testimages

#------------------------------------------------------------------------------
def exifdata_tostring(stored_bytes, datatype, decoder):
    """Convert Exif value to displayable string, based on datatype.

    1st parameter = Exif value as a byte string (as stored in Jpeg file)
    2nd parameter = Exif datatype, as an integer
    3rd parameter = reference to an ExifDecoder object, for decoding
                    byte strings to integer values based on the byte
                    alignment setting stored in the Jpeg file

    Returns a human-readable string version of the value.
    """
    displaystring = ''

    if datatype == 1:
        # Exif datatype 1 = BYTE (8-bit unsigned integer)
        displaystring = str(struct.unpack('B', stored_bytes)[0])
    elif datatype == 2:
        # Exif datatype 2 = ASCII (7-bit values, null-terminated)
        displaystring = ''
        mask = 0b01111111
        for byte in stored_bytes:
            displaystring += chr(byte & mask) # clear 8th bit
    elif datatype == 3:
        # Exif datatype 3 = SHORT (16-bit unsigned integer)
        displaystring = str(decoder.decode_bytes(stored_bytes[0:2]))
    elif datatype == 4:
        # Exif datatype 4 = LONG (32-bit unsigned integer)
        displaystring = str(decoder.decode_bytes(stored_bytes[0:4]))
    elif datatype == 5:
        # Exif datatype 5 = RATIONAL (fraction expressed as two LONGs,
        # first is numerator and second is denominator)
        numerator = decoder.decode_bytes(stored_bytes[0:4])
        denominator = decoder.decode_bytes(stored_bytes[4:8])
        displaystring = str(numerator) + '/' + str(denominator)
    elif datatype == 6:
        # Exif datatype 6 = SBYTE (8-bit signed integer, 2s complement)
        displaystring = struct.unpack_from('b', stored_bytes[0])
    elif datatype == 7:
        # Exif datatype 7 = UNDEFINED (one 8-bit byte of any value)
        displaystring = stored_bytes[0]
    elif datatype == 8:
        # Exif datatype 8 = SSHORT (signed SHORT, 16-bit signed
        # integer, 2s complement notation)
        displaystring = str(decoder.decode_bytes(stored_bytes[0:2]))
    elif datatype == 9:
        # Exif datatype 9 = SLONG (signed LONG, 32-bit signed
        # integer, 2s complement notation)
        displaystring = str(decoder.decode_bytes(stored_bytes[0:4]))
    elif datatype == 10:
        # Exif datatype 10 = SRATIONAL (signed rational, a fraction
        # expressed as two SLONGs; first is numerator and second is
        # denominator)
        numerator = decoder.decode_bytes(stored_bytes[0:4])
        denominator = decoder.decode_bytes(stored_bytes[4:8])
        displaystring = str(numerator) + '/' + str(denominator)
    else:
        # unknown data type, so just return the raw data
        displaystring = str(stored_bytes)

    return displaystring

#------------------------------------------------------------------------------
def read_app0_jfif(imagefile, seg_offset, meta_dict):
    """Read JFIF metadata from an APP0 segment and store in dictionary.

    1st parameter  = file handle for jpeg file, opened as 'rb' read binary
    2nd parameter = the offset of the APP0 segment to be processed
    3rd parameter  = dictionary being created by readmeta(); found Exif metadata
                 will be added to this dictionary
    """
    imagefile.seek(seg_offset, 0) # go to this APP0 segment
    verify_marker(imagefile, 'APP0')
    _ = imagefile.read(2) # skip over the APP0 data size value

    jfifheader = verify_jfifheader(imagefile)
    meta_dict['JFIF|Identifier'] = (jfifheader, '', '', 1)
    _ = imagefile.read(7) # skip over next 7 bytes
    xthumb_bytestr = imagefile.read(1)
    xthumb_int = struct.unpack('B', xthumb_bytestr)[0]
    meta_dict['JFIF|Xthumbnail'] = (str(xthumb_int), '', '', 1)
    ythumb_bytestr = imagefile.read(1)
    ythumb_int = struct.unpack('B', ythumb_bytestr)[0]
    meta_dict['JFIF|Ythumbnail'] = (str(ythumb_int), '', '', 1)

#------------------------------------------------------------------------------
def read_app1_exif(imagefile, seg_offset, meta_dict):
    """Read Exif metadata from an APP1 segment and store in dictionary.

    1st parameter = file handle for jpeg file, opened as 'rb' read binary
    2nd parameter = the offset of the APP1 segment to be processed
    3rd parameter = dictionary being created by readmeta(); found Exif metadata
                    will be added to this dictionary
    """

    # See section 4.6.3 of Exif 2.3, "Exif-specific IFDs"
    subifd_queue = deque() # queue of offsets for all exif sub-IFDs found

    imagefile.seek(seg_offset, 0) # go to this APP1 segment
    verify_marker(imagefile, 'APP1')
    _ = imagefile.read(2) # skip over the APP1 data size value
    verify_exifheader(imagefile)
    tiff_header, byte_order, offset_ifd0 = verify_tiffheader(imagefile)

    # Iterate through the IFDs in this segment
    offset_ifd = offset_ifd0
    while offset_ifd > 0:
        imagefile.seek(tiff_header + offset_ifd) # start of IFD
        offset_ifd = \
            read_ifd(imagefile, byte_order, meta_dict, subifd_queue)

    # process subifd_queue (see "4.6.3 Exif-specific IFD" in Exif 2.3)
    while len(subifd_queue) > 0:
        offset_ifd = subifd_queue.popleft()
        while offset_ifd > 0:
            imagefile.seek(tiff_header + offset_ifd) # start of IFD
            offset_ifd = \
                read_ifd(imagefile, byte_order, meta_dict, subifd_queue)

#------------------------------------------------------------------------------
def read_app1_xmp(imagefile, seg_offset, meta_dict):
    """Read XMP metadata from an APP1 segment and store in dictionary.

    1st parameter = file handle for jpeg file, opened as 'rb' read binary
    2nd parameter = the offset of the APP1 segment to be processed
    3rd parameter = dictionary being created by readmeta(); found XMP metadata
                    will be added to this dictionary

    Updates the dictionary with metadata values found in this segment.
    """
    imagefile.seek(seg_offset, 0) # go to this APP1 segment
    verify_marker(imagefile, 'APP1')

    # get APP1 data size
    datasize = struct.unpack('>H', imagefile.read(2))[0]

    # skip over the 29-byte XMP identifier, get to start of the data
    _ = imagefile.read(29)

    # read the contents of this APP1, and extract the XMP packet
    payload_size = datasize - 29 - 2
    app1_payload = imagefile.read(payload_size)

    # Notethat the xpacket end tag can contain either single or double
    # quotes around the end attribute value ('w'), so we use a regex
    search_obj = re.search(r'<\?xpacket end=[\'"]w[\'"]\?>',
                           app1_payload.decode('utf8'), re.I)
    if not search_obj:
        print("ERROR: no closing tag found for XMP packet in APP1 segment!")
        return
    closing_tag_pos = search_obj.span()[0] + 2
    if closing_tag_pos == 0:
        xmp_packet = b''
    else:
        xmp_packet = app1_payload[:closing_tag_pos + len('<?xpacket end="w"?>')]

    for child in fromstring(xmp_packet.decode('utf8')).iter():
        tag_value = child.text
        if not str(tag_value).strip():
            continue # no value to save

        # expected syntax: {namespace}tagname
        match_obj = re.search(r'{(?P<ns>.+)}(?P<tag>.+)', child.tag)
        if match_obj:
            xmp_ns = match_obj.group('ns')
            tagname = match_obj.group('tag')
            meta_dict[xmpns_tagtype(xmp_ns) + '|' + tagname] = (tag_value, '', '', 1)

#------------------------------------------------------------------------------
def read_app1_xmpext(imagefile, seg_offset, meta_dict):
    """Read XMP Extended metadata from an APP1 segment and store in dictionary.

    1st parameter = file handle for jpeg file, opened as 'rb' read binary
    2nd parameter = the offset of the APP1 segment to be processed
    3rd parameter = dictionary being created by readmeta(); found XMP Extended metadata
                    will be added to this dictionary
    """
    imagefile.seek(seg_offset, 0) # go to this APP1 segment
    verify_marker(imagefile, 'APP1')
    # skip over the 2-byte APP1 data size value
    _ = imagefile.read(2)
    # skip over the 35-byte XMP Extended identifier, get to start of the data
    _ = imagefile.read(35)
    meta_dict['XMP-extended|///ToDo'] = \
        ('offset = {0}'.format(seg_offset), '', '', 1)

#------------------------------------------------------------------------------
def read_app12(imagefile, seg_offset, meta_dict):
    """Read metadata from an APP12 segment and store in dictionary.

    1st parameter = file handle for jpeg file, opened as 'rb' read binary
    2nd parameter = the offset of the APP12 segment to be processed
    3rd parameter = dictionary being created by readmeta(); found Exif metadata
                    will be added to this dictionary
    """
    imagefile.seek(seg_offset, 0) # go to this APP12 segment
    verify_marker(imagefile, 'APP12')
    meta_dict['APP12|///ToDo'] = \
        ('offset = {0}'.format(seg_offset), '', '', 1)

#------------------------------------------------------------------------------
def read_app13(imagefile, seg_offset, meta_dict):
    """Read metadata from an APP13 segment and store in dictionary.

    1st parameter = file handle for jpeg file, opened as 'rb' read binary
    2nd parameter = the offset of the APP13 segment to be processed
    3rd parameter = dictionary being created by readmeta(); found Exif metadata
                    will be added to this dictionary
    """
    imagefile.seek(seg_offset, 0) # go to this APP12 segment
    verify_marker(imagefile, 'APP13')
    meta_dict['APP13|///ToDo'] = \
        ('offset = {0}'.format(seg_offset), '', '', 1)

#------------------------------------------------------------------------------
def read_ifd(filehandle, byte_order, meta_dict, subifd_queue):
    """Read an Image File Directory (IFD).

    1st parameter = handle of open jpeg file, positioned to the first
                    byte of the IFD to be read
    2nd parameter = the byte alignment setting as stored in the first 2 bytes
                    of the file's TIFF Header:
                    b'II' = Intel-style "little endian" encoding is used
                    b'MM' = Motorola-style "big endian" encoding is used
    3rd parameter = reference to the dictionary of metadata being created by
                    readmeta() - found tags/values are added to the dictionary
    4th parameter = reference to the deque used for storing Exif-specific IFDs
                    (aka "sub-IFDs") to be processed

    Returns the offset of the next IFD in this segment, or 0 if that was the
    last IFD in the segment.
    """
    decoder = ExifDecoder(byte_order)

    directory_entries = decoder.decode_bytes(filehandle.read(2))
    for _ in range(directory_entries):

        exif_tag_no = decoder.decode_bytes(filehandle.read(2))
        data_type = decoder.decode_bytes(filehandle.read(2))
        number_of_values = decoder.decode_bytes(filehandle.read(4))
        tagdata = filehandle.read(4)
        if exif_tag_no in (34665, 34853, 40965):
           # these tags are offsets to Exif-specific IFDs, so add to the
           # sub-IFD queue for processing later
            subifd_queue.append(decoder.decode_bytes(tagdata))

        else:
            # this is metadata, so add to the metadata dictionary
            tagname = exiftag(exif_tag_no)
            dict_key = 'Exif|' + tagname
            tagvalue = exifdata_tostring(tagdata, data_type, decoder)
            meta_dict[dict_key] = (tagvalue, str(exif_tag_no), data_type, number_of_values)

    # return the offset to the next IFD
    return decoder.decode_bytes(filehandle.read(4))

#------------------------------------------------------------------------------
def readmeta(jpg_file):
    """Read metadata from a JPEG file.

    1st parameter = filename

    Returns a dictionary with this structure:
        keys = tagtype|tagname
        values = (tagdata, tagno, datatype, numvals)

    Note that tagno/datatype/numvals are only used with true Exif tags;
    i.e., when tagtype == 'Exif'.
    """
    metadata_list = {} # dictionary of metadata found (Exif, XMP, etc)

    with open(jpg_file, 'rb') as imagefile:
        segment_list = segment_map(imagefile)
        for segmark, seg_offset in segment_list:
            if segmark == 'APP0':
                read_app0_jfif(imagefile, seg_offset, metadata_list)
            if segmark == 'APP1-Exif':
                read_app1_exif(imagefile, seg_offset, metadata_list)
            elif segmark == 'APP1-XMP':
                read_app1_xmp(imagefile, seg_offset, metadata_list)
            elif segmark == 'APP1-XMPext':
                read_app1_xmpext(imagefile, seg_offset, metadata_list)
            elif segmark == 'APP12':
                read_app12(imagefile, seg_offset, metadata_list)
            elif segmark == 'APP13':
                read_app13(imagefile, seg_offset, metadata_list)

    return metadata_list

#------------------------------------------------------------------------------
def readmeta_print(filename, tag_dict):
    """Pretty-print  tag dictionary created by readmeta().

    1st parameter = filename
    2nd parameter = the tag dictionary returned by readmeta()
    """
    print((' ' + filename + ' ').center(71, '-')[:71])
    print(54*' ' + 'Exif  Data # of')
    print('Tag Type     Tag Name (truncated) Value               Tag #' + ' ' + 'Type values')
    print(12*'-' + ' ' + 20*'-' + ' ' + 19*'-' + ' ' + 5*'-' + ' ' + 4*'-' + ' ' + 6*'-')

    for tagtype_name in sorted(tag_dict):
        tagtype, tagname = tagtype_name.split('|')
        tagdata, tagno, datatype, numvals = tag_dict[tagtype_name]
        print(tagtype.ljust(12)[:12] + ' ' +
              tagname.ljust(20)[:20] + ' ' +
              str(tagdata).ljust(19)[:19] + ' '  +
              str(tagno).ljust(5)[:5] + ' ' +
              str(datatype).ljust(2)[:2] + '   ' +
              str(numvals).ljust(6)[:6])

#------------------------------------------------------------------------------
def segment_map(filehandle):
    """Get the map of all segments in a jpeg file.

    1st parameter = file handle of jpeg file, open for binary read

    Returns a list of tuples corresponding to the segments in the file,
    in the order they occur in the file. Each tuple contains a segment
    ID and an absolute offset in the file; e.g., ('APP1', 2).

    Note: we stop at EOI (End Of Image) or SOS (Start Of Scan). This
    means that we ignore any segments that might occur after SOS -- a
    theoretical possibility, although we've never seen a Jpeg structured
    in that manner and stopping at SOS provides better performance
    because we don't have to process any image data.
    """
    segments = [] # initialize the list of segments
    filehandle.seek(2, 0) # first segment starts right after the SOI

    while True:
        seg_mark = filehandle.read(2)
        if len(seg_mark) < 2:
            break # file parsing error: we've reached EOF unexpectedly

        seg_id = seginfo(seg_mark)['name']

        if seg_id == 'APP1':
            # determine whether APP1 format is Exif, XMP, or XMP Extended
            filepos = filehandle.tell() # note current file position
            _ = filehandle.read(2) # skip over thec data size value
            id_str = filehandle.read(35) # APP1 identification string
            if id_str[:6] == b'Exif\x00\x00':
                segments.append(('APP1-Exif', filepos-2))
            elif id_str[:29] == b'http://ns.adobe.com/xap/1.0/\x00':
                segments.append(('APP1-XMP', filepos-2))
            elif id_str[:35] == b'http://ns.adobe.com/xmp/extension/\x00':
                segments.append(('APP1-XMPext', filepos-2))
            else:
                segments.append(('APP1-unknown', filepos-2))

            filehandle.seek(filepos, 0) # return to current file position
        else:
            # non-APP1 segment, add it to the list
            segments.append((seg_id, filehandle.tell()-2))

        if seg_id == 'EOI' or seg_id == 'SOS':
            break # stop processing the image

        if seg_mark in [b'\xff\x01', b'\xff\xd0', b'\xff\xd1', b'\xff\xd2',
                        b'\xff\xd3', b'\xff\xd4', b'\xff\xd5', b'\xff\xd6',
                        b'\xff\xd7', b'\xff\xd8', b'\xff\xd9']:
            # These segment markers have no payload, so we're already
            # positioned for the next segment after reading the segment marker
            datasize = 0
        else:
            dsbytes = filehandle.read(2)
            if len(dsbytes) < 2:
                break # file parsing error: we've reached EOF unexpectedly
            datasize = struct.unpack('>H', dsbytes)[0]
            # skip forward to next segment, ready to repeat the loop
            filehandle.seek(datasize-2, 1)

    return segments

#------------------------------------------------------------------------------
def verify_exifheader(filehandle=None):
    """Verify the 6-byte Exif header.

    filehandle = handle of open Jpeg file, positioned to the Exif header

    Checks the next 6 bytes and exits program with error message if the
    expected value is not found.

    Note: file position is advanced 6 bytes by this function.
    """
    exif_header = filehandle.read(6)
    if exif_header != b'Exif\x00\x00':
        print("INVALID Exif header:", exif_header)
        sys.exit()

#------------------------------------------------------------------------------
def verify_jfifheader(filehandle=None):
    """Verify the 5-byte JFIF header.

    filehandle = handle of open Jpeg file, positioned to the JFIF header

    Checks the next 5 bytes and exits program with error message if an
    allowed value is not found.
    Returns the 5 bytes that were read.

    Note: file position is advanced 5 bytes by this function.
    """
    jfif_header = filehandle.read(5)

    if jfif_header not in [b'JFIF\x00', b'JFXX\x00']:
        print("INVALID JFIF header:", jfif_header)
        sys.exit()

    return jfif_header

#------------------------------------------------------------------------------
def verify_marker(filehandle=None, markertype=None):
    """Verify a 2-byte segment marker in the Jpeg file.

    filehandle = handle of open Jpeg file, positioned to the marker
    markertype = expected marker type ('SOI', 'APP1', etc.)

    Checks the marker and exits program with error message if the expected
    value is not found.

    Note: file position is advanced 2 bytes by this function.
    """
    marker = filehandle.read(2)

    if markertype not in ['SOI', 'APP0', 'APP1', 'APP2', 'APP3', 'APP12',
                          'APP13', 'APP14']:
        print('Unknown marker type passed to verify_marker(): ' +
              markertype)
        sys.exit()

    if markertype == 'SOI' and marker != b'\xff\xd8':
        print('ERROR: SOI expected but not found.' + str(marker))
        sys.exit()
    elif markertype == 'APP0' and marker != b'\xff\xe0':
        print('ERROR: APP0 expected but not found.' + str(marker))
    elif markertype == 'APP1' and marker != b'\xff\xe1':
        print('ERROR: APP1 expected but not found.' + str(marker))
    elif markertype == 'APP2' and marker != b'\xff\xe2':
        print('ERROR: APP2 expected but not found.' + str(marker))
    elif markertype == 'APP3' and marker != b'\xff\xe3':
        print('ERROR: APP3 expected but not found.' + str(marker))
    elif markertype == 'APP12' and marker != b'\xff\xec':
        print('ERROR: APP12 expected but not found.' + str(marker))
    elif markertype == 'APP13' and marker != b'\xff\xed':
        print('ERROR: APP13 expected but not found.' + str(marker))
    elif markertype == 'APP14' and marker != b'\xff\xee':
        print('ERROR: APP14 expected but not found.' + str(marker))

#------------------------------------------------------------------------------
def verify_tiffheader(filehandle=None):
    """Verify the 8-byte TIFF header.

    filehandle = handle of open Jpeg file, positioned to the marker

    Checks the next 8 bytes and exits program with error message if the
    expected values are not found.

    Returns a tuple containing the three values read from the TIFF header:
    (tiff header offset, byte alignment order, offset to IFD0)
    """
    tiff_header = filehandle.tell()
    byte_alignment = filehandle.read(2)
    testdecoder = ExifDecoder(byte_alignment)

    # verify sample encoding of x2A (42 decimal)
    sample_encoding = testdecoder.decode_bytes(filehandle.read(2))
    if sample_encoding != 42:
        print("Sample encoded value: INCORRECT", sample_encoding)
        sys.exit()
    ifd0 = testdecoder.decode_bytes(filehandle.read(4))

    return (tiff_header, byte_alignment, ifd0)

#------------------------------------------------------------------------------
def xmpns_tagtype(xmp_namespace):
    """Convert an XMP namespace to tagtype identifier.

    1st parameter = XM namespace string
    Returns a tag-type identifier, used to identify the source of
    each metadata value returned in the master dictionary.
    """
    tagtype = xmp_namespace # default is the full namespace
    if xmp_namespace == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#':
        tagtype = 'XMP-RDF'
    elif xmp_namespace == 'http://ns.adobe.com/tiff/1.0/':
        tagtype = 'XMP-tiff'
    elif xmp_namespace == 'http://ns.adobe.com/xap/1.0/':
        tagtype = 'XMP-xap'
    elif xmp_namespace == 'http://ns.adobe.com/exif/1.0/':
        tagtype = 'XMP-exif'
    elif xmp_namespace == 'http://ns.adobe.com/xap/1.0/mm/':
        tagtype = 'XMP-xap'
    elif xmp_namespace == 'http://purl.org/dc/elements/1.1/':
        tagtype = 'XMP-dcore'
    elif xmp_namespace == 'http://ns.adobe.com/photoshop/1.0/':
        tagtype = 'Photoshop'
    return tagtype

#------------------------------------------------------------------------------
class ExifDecoder(object):
    """Decode byte strings from a Jpeg/Exif file.

    Afer initializing an ExifDecoder, use the decode_bytes() method to
    decode values that are read from the file.
    """
    def __init__(self, endian=None):
        self.byteorder = '<' # default is Intel-style little-endian encoding
        if endian != None:
            self.set_byteorder(bytealign=endian)

    def set_byteorder(self, bytealign=None, filename=None):
        """Set byte order for decoding byte strings.

        bytealign = the byte alignment setting as stored in the first 2 bytes
                    of the file's TIFF Header:
                    b'II' = Intel-style "little endian" encoding is used
                    b'MM' = Motorola-style "big endian" encoding is used
        filename = a JPEG file whose byte alignment setting should be used.
                   If filename is provided, bytealign parameter is ignored.

        Sets self.byteorder to '<' or '>' as appropriate.
        """
        if filename:
            with open(filename, 'rb') as jpeg_source:
                _ = jpeg_source.read(12) # skip the the TIFF header
                bytealign = jpeg_source.read(2)

        if bytealign not in [b'II', b'MM']:
            print('WARNING: invalid endian setting in ExifDecoder - ' +
                  str(bytealign))
        self.byteorder = '<' if bytealign == b'II' else '>'

    def decode_bytes(self, byte_string):
        """Decode a byte string, based on current endian setting.
        """
        if len(byte_string) == 0:
            return 0

        if len(byte_string) == 2:
            return struct.unpack(self.byteorder+'H', byte_string)[0]
        elif len(byte_string) == 4:
            return struct.unpack(self.byteorder+'I', byte_string)[0]
        else:
            print("Invalid byte string passed to ExifDecoder:", str(byte_string))

#------------------------------------------------------------------------------
if __name__ == "__main__":
    TESTFILES = testimages()
    for fname in TESTFILES:
        tag_list = readmeta(fname)
        readmeta_print(fname, tag_list)
        print('')
