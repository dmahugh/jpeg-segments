"""Data structures for Jpeg metadata extraction.

exiftag() converts exif tag number (int) to tag description
seginfo() converts segment marker to dictionary of segment info
testimages() returns a list of Jpeg images for testing
"""
import json
import os

# create Exif tags dictionary from JSON file
with open('tagnames_exif23.json', 'r') as tagsfile:
    EXIF_TAGS = json.load(tagsfile)

#------------------------------------------------------------------------------
def exiftag(tagno):
    """Convert Exif tag number (string) to description (string)

    These tag numbers/names are defined in the Exif 2.3 specification.
    """
    tagno_str = str(tagno)
    if tagno_str in EXIF_TAGS:
        return EXIF_TAGS[tagno_str]
    else:
        return tagno_str + '?'

#------------------------------------------------------------------------------
def seginfo(segment_marker):
    """Convert segment marker to dictionary of segment info.

    For example, b'\xff\xe1' is converted to a dictionary with these
    key/value pairs: name: 'APP1', has_data: True, has_meta: True

    has_data = whether this segment type has a data size in bytes 3-4 and
               a data payload starting at byte 5; if False, then this
               segment type is justa 2-byte segment marker (e.g., SOI/EOI)

    has_meta = whether this segment type contains metadata to be
               retrieved (i.e., Exif/JFIF/XMP/other metadata).

    Most of these segment types are defined in Exif 2.3, and some
    additional information on other segment types can be found here:
    http://www.ozhiker.com/electronics/pjmt/jpeg_info/app_segments.html
    """
    segdata = {b'\xff\x01':{'name':'ff01', 'has_data':False, 'has_meta':False},
               b'\xff\xe0':{'name':'APP0', 'has_data':True, 'has_meta':True},
               b'\xff\xe1':{'name':'APP1', 'has_data':True, 'has_meta':True},
               b'\xff\xe2':{'name':'APP2', 'has_data':True, 'has_meta':True},
               b'\xff\xe3':{'name':'APP3', 'has_data':True, 'has_meta':True},
               b'\xff\xe4':{'name':'APP4', 'has_data':True, 'has_meta':True},
               b'\xff\xe5':{'name':'APP5', 'has_data':True, 'has_meta':True},
               b'\xff\xe6':{'name':'APP6', 'has_data':True, 'has_meta':True},
               b'\xff\xe7':{'name':'APP7', 'has_data':True, 'has_meta':True},
               b'\xff\xe8':{'name':'APP8', 'has_data':True, 'has_meta':True},
               b'\xff\xe9':{'name':'APP9', 'has_data':True, 'has_meta':True},
               b'\xff\xea':{'name':'APP10', 'has_data':True, 'has_meta':True},
               b'\xff\xeb':{'name':'APP11', 'has_data':True, 'has_meta':True},
               b'\xff\xec':{'name':'APP12', 'has_data':True, 'has_meta':True},
               b'\xff\xed':{'name':'APP13', 'has_data':True, 'has_meta':True},
               b'\xff\xee':{'name':'APP14', 'has_data':True, 'has_meta':True},
               b'\xff\xef':{'name':'APP15', 'has_data':True, 'has_meta':True},
               b'\xff\xfe':{'name':'COM', 'has_data':True, 'has_meta':False},
               b'\xff\xc4':{'name':'DHT', 'has_data':True, 'has_meta':False},
               b'\xff\xdb':{'name':'DQT', 'has_data':True, 'has_meta':False},
               b'\xff\xdd':{'name':'DRI', 'has_data':True, 'has_meta':False},
               b'\xff\xd9':{'name':'EOI', 'has_data':False, 'has_meta':False},
               b'\xff\xd0':{'name':'RST0', 'has_data':False, 'has_meta':False},
               b'\xff\xd1':{'name':'RST1', 'has_data':False, 'has_meta':False},
               b'\xff\xd2':{'name':'RST2', 'has_data':False, 'has_meta':False},
               b'\xff\xd3':{'name':'RST3', 'has_data':False, 'has_meta':False},
               b'\xff\xd4':{'name':'RST4', 'has_data':False, 'has_meta':False},
               b'\xff\xd5':{'name':'RST5', 'has_data':False, 'has_meta':False},
               b'\xff\xd6':{'name':'RST6', 'has_data':False, 'has_meta':False},
               b'\xff\xd7':{'name':'RST7', 'has_data':False, 'has_meta':False},
               b'\xff\xc0':{'name':'SOF0', 'has_data':True, 'has_meta':False},
               b'\xff\xc2':{'name':'SOF2', 'has_data':True, 'has_meta':False},
               b'\xff\xd8':{'name':'SOI', 'has_data':False, 'has_meta':False},
               b'\xff\xda':{'name':'SOS', 'has_data':True, 'has_meta':False}}

    if segment_marker in segdata:
        return segdata[segment_marker]
    else:
        # unknown segment marker
        hexname = ''.join('{:02x}'.format(char) for char in segment_marker)
        return {'name': hexname + '?', 'has_data': False, 'has_meta': False}

#------------------------------------------------------------------------------
def testimages(filtercond=None):
    """Get a list of Jpeg image filenames for testing.

    filtercond = optional string that occurs in filename (e.g., 'XMP')

    Notes:
    - returns filenames from a 'testimages' subfolder
    - returned filenames include folder (e.g., 'testimages/whatever.jpg')
    - filtering is case-insensitive
    """
    filenames = []
    for filename in os.listdir('testimages'):
        if filename.lower().endswith('.jpg'):
            if filtercond is None or filtercond.lower() in filename.lower():
                filenames.append('testimages/' + filename)
    return filenames

#------------------------------------------------------------------------------
if __name__ == '__main__':

    print('-'*42)
    print('seginfo() tests:')
    print('-'*42)
    # test data is tuples with expected values for name, has_data, has_meta
    TESTSEGS = {
        b'\xff\x01': ('ff01', False, False),
        b'\xff\xe0': ('APP0', True, True),
        b'\xff\xe1': ('APP1', True, True),
        b'\xff\xed': ('APP13', True, True),
        b'\xff\xda': ('SOS', True, False)}
    for testseg in TESTSEGS:
        expected = TESTSEGS[testseg]
        testdata = seginfo(testseg)
        actual = (testdata['name'], testdata['has_data'],
                  testdata['has_meta'])
        result = 'PASSED' if expected == actual else 'FAILED'
        print('|-- ' + result + ': ' + str(testseg) + ' -> ' + testdata['name'])

    print('-'*42)
    print('exiftag() tests:')
    print('-'*42)
    TESTTAGS = [('256', 'ImageWidth'), ('37385', 'Flash'),
                ('315', 'Artist'), ('36864', 'ExifVersion'),
                ('37377', 'ShutterSpeedValue')]
    for testtag in TESTTAGS:
        result = 'PASSED' if exiftag(testtag[0]) == testtag[1] else 'FAILED'
        print('|-- ' + result + ': ' + str(testtag))

    print('-'*42)
    print("testimages('Flickr'):")
    print('-'*42)
    for testimg in testimages('Flickr'):
        print('|-- ' + testimg)
