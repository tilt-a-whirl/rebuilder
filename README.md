# rebuilder
Rebuilds one image using tiles from another image

This script takes a "memory" image and a "portrait" image as input (or whatever images you like) and outputs a new 
portrait rebuilt using blocks from the memory image. 

Type ./rebuilder.py -h for usage.

Currently, the source or "memory" image is required to be 512 x 512 pixels. I'm hoping to make this more flexible
in a future version.

This script was originally written in Python 2.5 on Mac OS X 10.6. Development is continuing under Python 2.7 on 
OS X Yosemite. To run, please make sure the PIL library is installed for your version. It can be found here:

http://www.pythonware.com/products/pil/

or here:

http://rudix.org/packages/pil.html

Feel free to read more about the project that inspired this tool here:

http://artful-i.com/2014/02/past-imperfect/
