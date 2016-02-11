# jpeg-segments

This repo contains programs used for analyzing and displaying the segments in
JPEG files. Test images should be located in a testimages subfolder, and when
jpegsegments.py is run as a standlone program it will display the segment
architecture of those JPG files.

- jpegsegments.py = main program to navigate JPEG segments
- jpegdata.py = module of Exif specification data and test data
- tagnames_exif23.json = tag names from the Exif 2.3 specification
- output.txt = sample output of jpegsegments.py

Here is the algorithm implemented by jpegsegments.py to identify the segments
in a JPEG file:

![flowchart](flowchart.png)

I've assembled a folder of test files that contain variations on the order and
type of segments in a JPEG image. Some of these are Copyright &copy; other
people so I can't include the images in the repo, but here's an example of the
output from jpegsegments.py for some of my test images:

![screenshot](output.png)
