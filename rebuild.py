#! /usr/bin/python

"""
rebuild.py by Amy Tucker

This rebuilds one image using the tiles of another image. It accepts two source 
images. Usage:
    rebuild.py srcFile destFile [-s blockSize -t type]
    -s blockSize: Size of tiles in destination image (resolution)
    -t: Create one single type (l, h, s, v, r, g, or b)
    
The output will be saved to the directory from which the script is called, in
a folder named 'output.' The output file name will be in the form 
destBaseName_srcBaseName_type.tif. For example, if the source image is called 
backyard.tif, and the destination image is called me.tif, the block size is 30 
and the type is luminance, the final output will be named me_backyard_30_l.tif 
and me_backyard_30_l_hdr.tiff. No matter the input file formats, the output 
will be a TIFF. Note: This has only been tested with TIFF files as input.  

When a type is not provided, images are processed using luminance (l), hue (h), 
saturation (s), value (v), red (r), green (g), blue (b), and all combinations,
resulting in 254 unique combinations (and output files), 508 including hdr 
versions of each.

"""

from PIL import Image
from random import randint
from optparse import OptionParser
from sys import stderr, argv
from math import sqrt
import os.path
import itertools

def processArgs():
    """
    Processes command line arguments
    """
    rebld_args = {}
        
    usage = "Usage: %prog srcImage destImage [options]"
    p = OptionParser(usage=usage)
    p.add_option("-s", action="store", dest="blockSize", \
                 help="Block size in pixels (def = 30)")
    p.add_option("-t", action="store", dest="type", \
                 help="Type (l, h, s, v, r, g or b - optional)")
    
    p.set_defaults(blockSize = 30)
    p.set_defaults(type = '')
    
    opts, args = p.parse_args()
    
    if (len(args) != 2):
        stderr.write("Wrong number of arguments\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-s blockSize -t type]\n")
        raise SystemExit(1)
    
    if (len(opts.type) > 1):
        stderr.write("Type only takes one parameter\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-s blockSize -t type]\n")
        raise SystemExit(1)
    
    if (opts.type != '' and opts.type not in 'lhsvrgb'):
        stderr.write("Type only takes l, h, s, v, r, g, or b\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-s blockSize -t type]\n")
        raise SystemExit(1)
    
    # Set filenames and additional options
    rebld_args['src'] = args[0]
    rebld_args['dest'] = args[1]
    
    rebld_args['blockSize'] = int(opts.blockSize)
    rebld_args['type'] = opts.type
        
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
    
def buildAlgorithmList(opts):
    """
    Builds list of algorithms
    """
    algs = []
    for i in range(1, len(opts)+1):
        for subset in itertools.combinations(opts, i):
            st = ''
            for char in subset:
                st = st + char
            algs.append(st)
                                    
    return algs
        
def loadImages(file1, file2):
    """
    Loads the source and destination images and returns both
    """
    # Open the images
    img1 = Image.open(file1)
    img2 = Image.open(file2)
    
    return (img1, img2)

def calculateSrcBlockSize(img):
    """
    Calculates block size for src image of any size, to be divided evenly
    into 256 square-ish tiles (as close as possible).
    """
    # 1024 / 512 = 2
    aspect = float(img.size[0]) / float(img.size[1])
    rows = sqrt(256.0 / aspect)
    cols = aspect * rows
    rows = round(rows)
    cols = round(cols)
    x = int(img.size[0] / cols)
    y = int(img.size[1] / rows)
    return (x, y)

def buildImageList(img, maxValue, blockDims):
    """
    Builds a list of average l h s v r g b, one for each block.
    """
    blockSizeX = blockDims[0]
    blockSizeY = blockDims[1]
    blockSize = blockSizeX * blockSizeY
    numBlocksX = int(img.size[0] / blockSizeX)
    numBlocksY = int(img.size[1] / blockSizeY)
    numBlocks = numBlocksX * numBlocksY
    
    # Build the list of average block hues, values, or saturations, then sort
    avgList = []    
    for i in range(numBlocks):
        start_x = int(i % numBlocksX) * blockSizeX
        start_y = int(i / numBlocksX) * blockSizeY
        end_x = start_x + blockSizeX
        end_y = start_y + blockSizeY
        blockBox = (start_x, start_y, end_x, end_y)
        block = img.crop(blockBox)
        colors = block.getcolors(blockSize)
        rsum, gsum, bsum = 0, 0, 0
        hsum, ssum, vsum = 0.0, 0.0, 0.0
        for item in colors:
            r = item[1][0]
            g = item[1][1]
            b = item[1][2]
            rsum += r * item[0]
            gsum += g * item[0]
            bsum += b * item[0] 
            h, s, v = RGBtoHSV(r, g, b)  # slower here but more accurate
            hsum += h * item[0]
            ssum += s * item[0]
            vsum += v * item[0]
        avg_r = rsum / float(blockSize)
        avg_g = gsum / float(blockSize)
        avg_b = bsum / float(blockSize)
        avg_l = (avg_r * 0.299) + (avg_g * 0.587) + (avg_b * 0.114)
        avg_h = hsum / float(blockSize)
        avg_s = ssum / float(blockSize)
        avg_v = vsum / float(blockSize)
        
        # Scale all to 0, maxValue and convert to int
        avg_l = int((avg_l / 255.0) * maxValue)
        avg_h = int((avg_h / 360.0) * maxValue)
        avg_s = int(avg_s * maxValue)
        avg_v = int((avg_v / 255.0) * maxValue)
        avg_r = int((avg_r / 255.0) * maxValue)
        avg_g = int((avg_g / 255.0) * maxValue)
        avg_b = int((avg_b / 255.0) * maxValue)
        
        # We store the original index and avg together as a tuple, 
        # because we will need to calculate the coordinates of where this 
        # block originally came from
        avgDict = {}
        avgDict['l'] = avg_l
        avgDict['h'] = avg_h
        avgDict['s'] = avg_s
        avgDict['v'] = avg_v
        avgDict['r'] = avg_r
        avgDict['g'] = avg_g
        avgDict['b'] = avg_b
        avgList.append(avgDict)
    
    # Return the list
    return avgList

def buildAverageLUT(dictList, alg):
    """
    Builds a lookup table from calculated averages
    """
    avgLUT = []
    for i in range(len(dictList)):
        alg_dict = dictList[i]
        alg_sum = 0.0
        if ('l' in alg):
            alg_sum += alg_dict['l']
        if ('h' in alg):
            alg_sum += alg_dict['h']
        if ('s' in alg):
            alg_sum += alg_dict['s']
        if ('v' in alg):
            alg_sum += alg_dict['v']
        if ('r' in alg):
            alg_sum += alg_dict['r']
        if ('g' in alg):
            alg_sum += alg_dict['g']
        if ('b' in alg):
            alg_sum += alg_dict['b']
        
        avg = int(alg_sum / len(alg))   
        avgLUT.append((i, avg))
        
    # Sort based on the second element of the tuple, i.e. the alg type
    avgLUT.sort(key=lambda tup: tup[1])
        
    return avgLUT

def buildOutputImage(images, lookups, sizeDict, hdr, alg):
    """
    Builds output image
    """
    # Expand tuples
    src = images[0]
    dest = images[1]
    
    srcList = lookups[0]
    destList = lookups[1]
    
    # Create and build an output file that is the same size as the original 
    # portrait file
    outfile = Image.new("RGB", (dest.size[0], dest.size[1]))
    
    # Calculate some block sizes and counts
    srcBlockSizeX = sizeDict['srcBlockSizeX']
    srcBlockSizeY = sizeDict['srcBlockSizeY']
    blockSize = sizeDict['blockSize']
    srcNumBlocksX = int(src.size[0] / srcBlockSizeX)
    destNumBlocksX = int(dest.size[0] / blockSize)
    destBlockSizeX = blockSize
    destBlockSizeY = blockSize
        
    srcNumBlocks = len(srcList)
    destNumBlocks = len(destList)
                
    # Create a coordinate lookup list based on whether the hdr option is on or 
    # off. If off, we look up the corresponding memory block using the actual 
    # luminance value of the portrait block. This can mean that not all memory 
    # blocks are used, due to some memory list indices not existing in the list 
    # of portrait luminance values. If hdr is on, then for each portrait
    # block, a memory block will be located by scaling the index of the 
    # portrait block. Actual luminance values will not correspond to indices 
    # in the memory list in this case, but this ensures that each block in the 
    # memory list will be used.
    scale = 1.0 / destNumBlocks * srcNumBlocks
    
    # These multipliers make it possible for us to avoid an if statement 
    # inside the loop. If hdr, multiply the 'scale * i' assignment by 1 and
    # the other by 0, otherwise the opposite. That way we only get one value
    # or the other.
    scale_mult = int(hdr)
    dest_mult = int(not hdr)
    
    for i in range(destNumBlocks):
        j = (int(scale * i) * scale_mult) + (int(destList[i][1]) * dest_mult)
        
        # Grab the source and destination list indices
        src_idx = srcList[j][0]
        dest_idx = destList[i][0]
        
        start_x = int(src_idx % srcNumBlocksX) * srcBlockSizeX
        start_y = int(src_idx / srcNumBlocksX) * srcBlockSizeY
        end_x = start_x + srcBlockSizeX
        end_y = start_y + srcBlockSizeY
        
        # Grab the source image block
        srcBlock = src.crop((start_x, start_y, end_x, end_y))
        
        # Randomly determine whether this block will be flipped and/or rotated
        flip = randint(0, 2)
        rotate = randint(0, 3)
        if (flip > 0):
            srcBlock = srcBlock.transpose(flip-1)
        if (rotate > 0):
            srcBlock = srcBlock.transpose(rotate-1)
            
        # If the portrait block size is not equal to the memory block size, 
        # resize the memory block to be the same size as the portrait block
        if (destBlockSizeX * destBlockSizeY != srcBlockSizeX * srcBlockSizeY):
            srcBlock = srcBlock.resize((destBlockSizeX, destBlockSizeY))
            
        # Calculate the coordinates of the portrait block to be replaced
        start_x = (dest_idx % destNumBlocksX) * destBlockSizeX
        start_y = (dest_idx / destNumBlocksX) * destBlockSizeY
        
        # Paste the memory block into the correct coordinates of the output file
        outfile.paste(srcBlock, (start_x, start_y))
        
    return outfile

def saveOutputImage(outfile, args, hdr, alg):
    """
    Saves the output image
    """
    # Save the final image
    srcFile = args['src']
    destFile = args['dest']
    size = str(args['blockSize'])
    head, tail = os.path.split(srcFile)
    sfile, ext = os.path.splitext(tail)
    head, tail = os.path.split(destFile)
    dfile, ext = os.path.splitext(tail)
    directory = "output/"
    if not os.path.exists(directory):
        os.makedirs(directory)
    outfileName = directory + dfile + "_" + sfile + "_" + size + "_" + alg
    if hdr:
        outfileName = outfileName + '_hdr.tif'
    else:
        outfileName = outfileName + '.tif'
    outfile.save(outfileName, "TIFF")
    print("Saved " + outfileName)
    
def RGBtoHSV(r, g, b):
    """
    Converts RGB to HSV
    """
    minRGB = min( r, g, b )
    maxRGB = max( r, g, b )
    v = float(maxRGB)
    delta = maxRGB - minRGB
    
    if (maxRGB > 0):
        s = delta / float(maxRGB)
    else:                       # r = g = b = 0 ; s = 0, h is undefined
        s = 0.0
        h = 0.0
        return (h, s, v)

    if (minRGB == maxRGB):
        h = 0.0
    elif (r == maxRGB):
        h = (g - b) / float(delta)            # between yellow & magenta
    elif (g == maxRGB):
        h = 2 + (b - r) / float(delta)        # between cyan & yellow
    else:
        h = 4 + (r - g) / float(delta)        # between magenta & cyan
    h *= 60.0                          # degrees
    if (h < 0.0):  
        h += 360.0
        
    return (h, s, v)
    
if __name__ == '__main__':
    """ 
    Main function
    """    
    args = processArgs()
    opts = ['l', 'h', 's', 'v', 'r', 'g', 'b']
    if (args['type'] != ''):
        algs = args['type']
    else:
        algs = buildAlgorithmList(opts)
    
    images = loadImages(args['src'], args['dest'])
    
    # Build the image lists only once; they won't change
    srcBlockSize = calculateSrcBlockSize(images[0])
    destBlockSize = (args['blockSize'], args['blockSize'])
    srcDictList = buildImageList(images[0], 255, srcBlockSize)
    destDictList = buildImageList(images[1], len(srcDictList), destBlockSize)
        
    # Pack up the sizes we'll need to pass to the output image builder
    sizeDict = {}
    sizeDict['blockSize'] = args['blockSize']
    sizeDict['srcBlockSizeX'] = srcBlockSize[0]
    sizeDict['srcBlockSizeY'] = srcBlockSize[1]
    
    for alg in algs:
        # Lookups change for each algorithm
        srcList = buildAverageLUT(srcDictList, alg)
        destList = buildAverageLUT(destDictList, alg)
        lookups = (srcList, destList)
        # Create the output based on the current algorithm
        output = buildOutputImage(images, lookups, sizeDict, False, alg)
        output_hdr = buildOutputImage(images, lookups, sizeDict, True, alg)
        # Save the output images
        saveOutputImage(output, args, False, alg)
        saveOutputImage(output_hdr, args, True, alg)
            
    print ("Finished!")