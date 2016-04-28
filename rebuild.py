#! /usr/bin/python

"""
rebuild.py by Amy Tucker

This rebuilds a "destination" image using the tiles of a "source" image. It 
accepts two images as input. Usage:

    rebuild.py srcFile destFile [-b blockSize -t type -n 
                                 -d -m medThreshold -s smallThreshold]
                                 
    -b blockSize      : size of tiles in destination image (default = 30)
    -t type           : create one single type (l, h, s, v, r, g, or b) or 
                        combo of any number of valid types (default = lhsvrgb)
    -n                : non-uniform block size, averages to blockSize 
                        (default = False)
    -d                : detail resolution (ignores non-uniform if set) 
                        (default = False)
    -m medThreshold   : medium size blocks (detail resolution only) will not
                        appear in areas where the color variance is below this
                        number (1-10, default = 5)
    -s smallThreshold : small blocks (detail resolution only) will not appear 
                        in areas where the color variance is below this number 
                        (1-10, default = 8)
                       
The output will be saved to the directory from which the script is called, in
a folder named 'output.' The output file name will be in the form 
destBaseName_srcBaseName_size_type.tif. For example, if the source image is 
backyard.tif, and the destination image is me.tif, the block size is 30 
and the type is luminance, the final output will be named me_backyard_30_l.tif 
and me_backyard_30_l_hdr.tif. If non-uniform blocks are used, the size will
be followed by 'n,' as in me_backyard_30n_l_hdr.tif. If the detail option is
specified, non-uniform block size will be ignored if set, and the file name
will appear as me_backyard_30d_l_hdr.tif. No matter the input file formats,
the output will be a TIFF. Note: Choose the best compression possible for
your input files, or none at all. See PIL documentation for supported input
file formats.

A note on non-uniform blocks: The sizes of the blocks are determined when the
script launches, so all images produced by a single run will show the same
block size pattern, but different runs will each be different from each other.
Setting block size will still influence the overall resolution of the pattern,
as variations are based on a percentage of the original block size.

If detail is specified, non-uniform flag will be ignored if set.

About types: You can specify one single type (such as 'l') or a combination
of types ('lgv'). You will get each separate type plus all combinations of
the letters you include in the string. Invalid letters will be ignored. When 
a type is not provided, images are processed using luminance (l), hue (h), 
saturation (s), value (v), red (r), green (g), blue (b), and all combinations,
resulting in 254 unique combinations (and output files) -- 508 including hdr 
versions of each.

About detail resolution: This image is created in three passes, with the final
two passes (medium and high resolution) being dependent on the color variance
of the pass before, in the areas where the new blocks would appear. Sensitivity
can be adjusted using the medium and high threshold values. Adjustment of these
values will provide the most pleasing variation of blocks in the final image. 
A higher threshold usually works best for a smaller area due to the block's
lower overall pixel count, causing variance values to generally be higher.
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
    p.add_option("-b", action="store", dest="blockSize", 
                 help="Block size in pixels (default = 30)")
    p.add_option("-t", action="store", dest="type", 
                 help="Type (l, h, s, v, r, g, b or combination - optional)")
    p.add_option("-n", action="store_true", dest="isNonUniform", 
                 help="Make block size non-uniform - optional")
    p.add_option("-d", action="store_true", dest="isDetail",
                 help="Use detail resolution - optional")
    p.add_option("-m", action="store", dest="medThreshold",
                 help="Medium res color variance threshold (1-10, default = 5)")
    p.add_option("-s", action="store", dest="smallThreshold",
                 help="High res color variance threshold (1-10, default = 8)")
    
    p.set_defaults(blockSize = 30)
    p.set_defaults(type = '')
    p.set_defaults(isNonUniform = False)
    p.set_defaults(isDetail = False)
    p.set_defaults(medThreshold = 5)
    p.set_defaults(smallThreshold = 8)
    
    opts, args = p.parse_args()
    
    # Create some temporary variables to validate before assigning to the 
    # args dict later
    temp_blockSize = int(opts.blockSize)
    temp_type = opts.type
    temp_isNonUniform = opts.isNonUniform
    temp_isDetail = opts.isDetail
    temp_medThreshold = int(opts.medThreshold)
    temp_smallThreshold = int(opts.smallThreshold) 
    
    # Check that we have two file names
    if (len(args) != 2):
        stderr.write("Wrong number of arguments\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-b blockSize -t type -n \n")
        stderr.write("       -d -m medThreshold -s smallThreshold]\n")
        raise SystemExit(1)
    
    # Check for valid files. PIL will check that they're valid images.
    if (not os.path.isfile(args[0])):
        stderr.write("Invalid source file\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-b blockSize -t type -n \n")
        stderr.write("       -d -m medThreshold -s smallThreshold]\n")
        raise SystemExit(1)
    
    if (not os.path.isfile(args[1])):
        stderr.write("Invalid destination file\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-b blockSize -t type -n \n")
        stderr.write("       -d -m medThreshold -s smallThreshold]\n")
        raise SystemExit(1)
    
    # Make sure we have a workable block size
    if temp_blockSize < 8 and temp_isDetail:
        stderr.write("Block size too small for detail option. Clamped to 8.\n")
        temp_blockSize = 8
    elif temp_blockSize < 4:
        stderr.write("Block size too small. Clamped to 4.\n")
        temp_blockSize = 4
    
    # Check for duplicate, invalid and extra chars in type string
    typeDict = {}
    for t in temp_type:
        if t in 'lhsvrgb':
            if typeDict.has_key(t):
                stderr.write("Duplicate type %s ignored\n" % t)
            else:
                typeDict[t] = 1
        else:
            stderr.write("Invalid type %s ignored\n" % t)
            
    # Check if detail flag overrides non-uniform flag
    if temp_isDetail and temp_isNonUniform:
        stderr.write("Detail is specified; non-uniform flag ignored.\n")
        temp_isNonUniform = False
    
    # Check threshold values
    if temp_isDetail:
        if temp_medThreshold < 1 or temp_medThreshold > 10:
            stderr.write("Medium threshold out of 1-10 range, set to 5.\n")
            opts.medThreshold = 5
        if temp_smallThreshold < 1 or temp_smallThreshold > 10:
            stderr.write("Small threshold out of 1-10 range, set to 8.\n")
            temp_smallThreshold = 8
    
    # Set filenames and additional options
    rebld_args['src'] = args[0]
    rebld_args['dest'] = args[1]
    
    rebld_args['blockSize'] = temp_blockSize
    rebld_args['type'] = typeDict.keys()
    rebld_args['isNonUniform'] = temp_isNonUniform
    rebld_args['isDetail'] = temp_isDetail
    rebld_args['medThreshold'] = temp_medThreshold
    rebld_args['smallThreshold'] = temp_smallThreshold
    
    return (rebld_args)
    
    
if __name__ == '__main__':
    """ 
    Main function
    """
    # Process arguments
    args = processArgs()
    
    # Build the algorithm list
    opts = 'lhsvrgb'
    if (len(args['type']) == 1):
        algs = args['type'] 
    elif (len(args['type']) > 1):
        algs = rutils.buildAlgorithmList(args['type'])
    else:
        algs = rutils.buildAlgorithmList(opts)
        
    # Set up some variables
    sourceName = args['src']
    destName = args['dest']
    isNonUniform = args['isNonUniform']
    isDetail = args['isDetail']
    userBlockSize = args['blockSize']
    userBlockSizeMed = 0
    userBlockSizeHigh = 0
    
    # Two extra destination images will be used if detail flag is set
    destMed = None
    destHigh = None
    
    # If detail resolution is set, we'll complete the same tasks for two 
    # additional destination images and manipulate the block size for all.
    if isDetail: 
        
        # We need to make sure our block size is an even number before using 
        # it. Probably safer to subtract 1 than add. We'll also need additional
        # block sizes for the other two images we'll pull from.
        if userBlockSize % 2 != 0:
            userBlockSize -= 1
            stderr.write("Even block size needed when detail flag is set.\n")
            stderr.write("Block size changed to %d.\n" % userBlockSize)
        userBlockSizeHigh = userBlockSize / 2
        userBlockSizeMed = userBlockSize
        userBlockSize = userBlockSize * 2
        
    # Create the source class instances and open the images
    source = rutils.SourceImage.fromFile(sourceName)
    dest = rutils.SourceImage.fromFile(destName, isNonUniform, isDetail)
    
    # Calculate internal data based on whether this is a source or
    # destination image. Passing the user-entered blockSize will flag the
    # image as a destination image.
    source.calculateBlockVars()
    dest.calculateBlockVars(userBlockSize)
    
    # Get the number of blocks in the source image. We'll use this to
    # send a maxValue when we build the average list.
    srcRows, srcCols = source.getRowsCols()
    maxValue = (srcRows * srcCols) - 1
    
    # Average lists are straightforward
    source.buildAverageList(maxValue)
    dest.buildAverageList(maxValue)
        
    # Repeat the above process for the additional detail images
    if isDetail:

        # Create the additional image instances. We'll use the actual image
        # from the first destination image created so we don't open the same
        # file three times.
        destImage = dest.getImage()
        destMed = rutils.SourceImage.fromImage(destImage, False, isDetail)
        destHigh = rutils.SourceImage.fromImage(destImage, False, isDetail)
        
        # We need to sync up the final image size with the main destination 
        # image. We'll use width and height overrides when calculating blocks 
        # in the additional images to make sure everything is the same size.
        destRows, destCols = dest.getRowsCols()
        width = destCols * userBlockSize
        height = destRows * userBlockSize
        
        destMed.calculateBlockVars(userBlockSizeMed, width, height)
        destHigh.calculateBlockVars(userBlockSizeHigh, width, height)
    
        # Build the average lists for each, using the maxValue calculated from
        # the common source image number of blocks
        destMed.buildAverageList(maxValue)
        destHigh.buildAverageList(maxValue)
            
    # Iterate through the image types and combinations we're processing and
    # create output images
    for atype in algs:
        
        # Create the output based on the current algorithm
        output = rutils.OutputImage(args, userBlockSize, atype)
        output_hdr = rutils.OutputImage(args, userBlockSize, atype, True)
        
        # Lookups change for each algorithm
        source.buildAverageLUT(atype)
        dest.buildAverageLUT(atype)
        
        # Build hdr and non-hdr versions
        if isDetail:
            destMed.buildAverageLUT(atype)
            destHigh.buildAverageLUT(atype)
            output.buildImage(source, dest, destMed, destHigh)
            output_hdr.buildImage(source, dest, destMed, destHigh)
        else:
            output.buildImage(source, dest)
            output_hdr.buildImage(source, dest)
                
        # Save the output images
        output.saveImage()
        output_hdr.saveImage()
                    
    print ("Finished!")