"""Tools for extracting metadata from Jpeg files.

seg2dict() - convert a Jpeg segment to a dictionary
segment_list() - create list of segment dictionaries from Jpeg file
"""
import struct
import sys
from jpegdata import seginfo, testimages

#------------------------------------------------------------------------------
def segment_list(filename=None):
    """Create list of segment dictionaries from a Jpeg file.

    filename = a Jpeg file
    returns a list of dictionaries, one per segment in the file.

    Note: since we're only interested in metadata, image data is ignored.
    """
    seg_list = []

    with open(filename, 'rb') as jpegfile:

        while True:
            seg = segment_read(jpegfile)
            seg_list.append(seg)
            nextseg = seg['next_segment']
            if nextseg:
                jpegfile.seek(nextseg)
            else:
                break

    return seg_list

#------------------------------------------------------------------------------
def segment_read(filehandle=None):
    """Convert a Jpeg segment to a dictionary.

    filehandle = Jpeg file open for binary read, positioned to first byte
                 of the segment

    Returns a dictionary with these keys:
        offset = offset of the segment within the Jpeg file
        segmark = the 2-byte segment marker
        segtype = name of this segment type (e.g., 'APP1')
        has_data = whether segment type has a data payload
        has_meta = whether segment type's payload contains metadata
        payload = segment's data payload
    """

    # initialize dictionary object
    segdict = {}
    segdict['offset'] = filehandle.tell()
    segdict['segmark'] = filehandle.read(2)
    segdict['payload'] = None # default value
    segdict['next_segment'] = None # default value

    # get info about this segment type and copy to dictionary
    segtype_info = seginfo(segdict['segmark'])
    segdict['segtype'] = segtype_info['name']
    segdict['has_data'] = segtype_info['has_data']
    segdict['has_meta'] = segtype_info['has_meta']

    # Stop processing the file when SOS or EOI segment reached. We do this
    # because we're only interested in reading metadata, and want to maximize
    # performance for scanning large numbers of images quickly. The SOS
    # segment is different from the others in that its " data size" is
    # merely the size of the SOS header. The compressed data imediately
    # follows, and this is by far the largest segment in a typical Jpeg file.
    # Furthermore, the compressed data must actually be scanned and decoded
    # to find the EOI marker that follows, and we want to avoid the need to
    # read all of that data.

    # Note: if we terminate at SOS then we should never actually see an EOI,
    # but we're checking for EOI as well here to allow for the case where a
    # Jpeg file has no image data and only metadata -- we've not seen this
    # in an actual Jpeg, but it's theoretically possible and by checking for
    # both SOS and EOI here we will gracefully handle any such file.

    if segdict['segtype'] in ['SOS', 'EOI']:
        return segdict

    # if this segment type has no data payload, then the next segment
    # starts right after the 2-byte segment marker
    if not segdict['has_data']:
        segdict['next_segment'] = segdict['offset'] + 2
        return segdict

    # read data size; note that this size includes the 2-byte size
    # itself but doesn't include the 2-byte segment marker
    datasize_bytes = filehandle.read(2)
    datasize = struct.unpack('>H', datasize_bytes)[0]

    # if segment contains metadata, save a copy in the segment's dictionary
    if segdict['has_meta']:
        segdict['payload'] = filehandle.read(datasize - 2)
    else:
        # no metadata to save, so just skip past the data
        filehandle.seek(datasize-2, 1)
    segdict['next_segment'] = filehandle.tell()

    return segdict

#------------------------------------------------------------------------------
if __name__ == '__main__':

    if len(sys.argv) > 1:
        # test files listed on command line
        TESTFILES = sys.argv[1:]
    else:
        # use test files from testimages subfolder
        TESTFILES = testimages()

    for fname in TESTFILES:
        print('-'*32, fname, '-'*32, sep='\n')
        segments = segment_list(fname)
        for segment in segments:
            print('|-- ' + segment['segtype'].ljust(5) + ' - ', end='')
            if segment['has_meta']:
                print('METADATA')
            else:
                if segment['has_data']:
                    print('image data')
                else:
                    print('segment marker only')
