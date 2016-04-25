#! /usr/bin/python

"""
rebuild.py by Amy Tucker

This rebuilds one image using the tiles of another image. It accepts two source 
images. Usage:
    rebuild.py srcFile destFile [-s blockSize -t type -n]
    -s blockSize: Size of tiles in destination image (default = 30)
    -t type: Create one single type (l, h, s, v, r, g, or b) (default = all)
    -n: Non-uniform block size, is average of blockSize (default = False)
    
The output will be saved to the directory from which the script is called, in
a folder named 'output.' The output file name will be in the form 
destBaseName_srcBaseName_size_type.tif. For example, if the source image is 
backyard.tif, and the destination image is me.tif, the block size is 30 
and the type is luminance, the final output will be named me_backyard_30_l.tif 
and me_backyard_30_l_hdr.tif. If non-uniform blocks are used, the size will
be followed by 'n,' as in me_backyard_30n_l_hdr.tif. No matter the input file 
formats, the output will be a TIFF. Note: Choose the best compression possible
for your input files, or none at all. See PIL documentation for supported
input file formats.

A note on non-uniform blocks: The sizes of the blocks are determined when the
script launches, so all images produced by a single run will show the same
block size pattern, but different runs will each be different from each other.
Setting block size will still influence the overall resolution of the pattern,
as variations are based on a percentage of the original block size.

When a type is not provided, images are processed using luminance (l), hue (h), 
saturation (s), value (v), red (r), green (g), blue (b), and all combinations,
resulting in 254 unique combinations (and output files) -- 508 including hdr 
versions of each.

"""

import rebuilderutils as rutils
from optparse import OptionParser
from PIL import Image
from sys import stderr, argv
import os.path

def processArgs():
    """
    Processes command line arguments
    """
    rebld_args = {}
        
    usage = "Usage: %prog srcImage destImage [options]"
    p = OptionParser(usage=usage)
    p.add_option("-s", action="store", dest="blockSize", 
                 help="Block size in pixels (def = 30)")
    p.add_option("-t", action="store", dest="type", 
                 help="Type (l, h, s, v, r, g or b - optional)")
    p.add_option("-n", action="store_true", dest="isNonUniform", 
                 help="Make block size non-uniform - optional")
    
    p.set_defaults(blockSize = 30)
    p.set_defaults(type = '')
    p.set_defaults(isNonUniform = False)
    
    opts, args = p.parse_args()
    
    if (len(args) != 2):
        stderr.write("Wrong number of arguments\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-s blockSize -t type -n]\n")
        raise SystemExit(1)
    
    if (len(opts.type) > 1):
        stderr.write("Type only takes one parameter\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-s blockSize -t type -n]\n")
        raise SystemExit(1)
    
    if (opts.type != '' and opts.type not in 'lhsvrgb'):
        stderr.write("Type only takes l, h, s, v, r, g, or b\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-s blockSize -t type -n]\n")
        raise SystemExit(1)
    
    # Set filenames and additional options
    rebld_args['src'] = args[0]
    rebld_args['dest'] = args[1]
    
    rebld_args['blockSize'] = int(opts.blockSize)
    rebld_args['type'] = opts.type
    rebld_args['isNonUniform'] = opts.isNonUniform
        
    # Check for valid files. PIL will check that they're valid images.
    if (not os.path.isfile(rebld_args['src'])):
        stderr.write("Invalid source file\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-s blockSize -t type]\n")
        raise SystemExit(1)
    
    if (not os.path.isfile(rebld_args['dest'])):
        stderr.write("Invalid destination file\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-s blockSize -t type]\n")
        raise SystemExit(1)
    
    return (rebld_args)
    
    
if __name__ == '__main__':
    """ 
    Main function
    """
    
    # Process arguments and build our list of algorithms, if necessary.
    args = processArgs()
    opts = ['l', 'h', 's', 'v', 'r', 'g', 'b']
    if (args['type'] != ''):
        algs = args['type']
    else:
        algs = rutils.buildAlgorithmList(opts)
            
    # Open the images
    source = rutils.SourceImage(args['src'], args['isNonUniform'])
    dest = rutils.SourceImage(args['dest'], args['isNonUniform'])
    
    # Calculate internal data based on whether this is a source or
    # destination image. Passing the user-entered blockSize will flag the
    # image as the destination image.
    source.calculateBlockVars()
    dest.calculateBlockVars(args['blockSize'])
    
    # Get the number of blocks in the source image. We'll use this to
    # send a maxValue when we build the average list.
    srcRows, srcCols = source.getRowsCols()
    maxValue = (srcRows * srcCols) - 1
    
    # Average lists are straightforward
    source.buildAverageList(maxValue)
    dest.buildAverageList(maxValue)
    
    for atype in algs:
        # Lookups change for each algorithm
        source.buildAverageLUT(atype)
        dest.buildAverageLUT(atype)
        
        # Create the output based on the current algorithm
        output = rutils.OutputImage(args, atype)
        output_hdr = rutils.OutputImage(args, atype, True)
        
        # Build hdr and non-hdr versions
        output.buildImage(source, dest)
        output_hdr.buildImage(source, dest)
    
        # Save the output images
        output.saveImage()
        output_hdr.saveImage()
                    
    print ("Finished!")