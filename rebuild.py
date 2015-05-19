#! /usr/bin/python

"""
rebuild.py by Amy Tucker

This rebuilds one image using the tiles of another image. It accepts two source 
images. Usage:
    rebuild.py srcFile destFile [-s blockSize -t]
    -s blockSize: Size of tiles in destination image (resolution)
    -t: Test mode (luminance only)
    
The output will be saved to the directory from which the script is called, in
a folder named 'output.' The output file name will be in the form 
destBaseName_srcBaseName_type.tif. For example, if the source image is called 
backyard.tif, and the destination image is called me.tif, the block size is 30 
and it's in test mode (luminance only), the final output will be named 
me_backyard_30_l.tif and me_backyard_30_l_hdr.tiff. No matter the input file 
formats, the output will be a TIFF. Note: This has only been tested with TIFF 
files as input.  

When not in test mode, images are processed using luminance (l), hue (h), 
saturation (s), value (v), red (r), green (g), blue (b), or any combination,
resulting in 254 possible combinations (and output files).

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
    p.add_option("-t", action="store_true", dest="test", \
                 help="Test mode (luminance only)")
    
    p.set_defaults(blockSize=30)
    p.set_defaults(test=False)
    
    opts, args = p.parse_args()
    
    if (len(args) != 2):
        stderr.write("Wrong number of arguments\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-s blockSize -t]\n")
        raise SystemExit(1)
    
    # Set filenames and additional options
    rebld_args['src'] = args[0]
    rebld_args['dest'] = args[1]
    
    rebld_args['blockSize'] = int(opts.blockSize)
    rebld_args['test'] = opts.test
        
    # Check for valid files. PIL will check that they're valid images.
    if (not os.path.isfile(rebld_args['src'])):
        stderr.write("Invalid source file\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-s blockSize -t]\n")
        raise SystemExit(1)
    
    if (not os.path.isfile(rebld_args['dest'])):
        stderr.write("Invalid destination file\n")
        stderr.write("Usage: %s srcImage destImage " % argv[0])
        stderr.write("[-s blockSize -t]\n")
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
    x = int(img.size[0] / rows)
    y = int(img.size[1] / cols)
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
        for item in colors:
            rsum += item[1][0] * item[0]
            gsum += item[1][1] * item[0]
            bsum += item[1][2] * item[0]            
        avg_r = int(rsum / blockSize)
        avg_g = int(gsum / blockSize)
        avg_b = int(bsum / blockSize)
        avgLum = (avg_r * 0.299) + (avg_g * 0.587) + (avg_b * 0.114)
        
        h, s, v = RGBtoHSV(avg_r, avg_g, avg_b)
        
        # Scale all to 0, maxValue and convert to int
        avgLum = int((avgLum / 255) * maxValue)
        h = int((h / 360) * maxValue)
        s = int(s * maxValue)
        v = int((v / 255) * maxValue)
        avg_r = int((avg_r / 255) * maxValue)
        avg_g = int((avg_g / 255) * maxValue)
        avg_b = int((avg_b / 255) * maxValue)
        
        # We store the original index and avg together as a tuple, 
        # because we will need to calculate the coordinates of where this 
        # block originally came from
        avgDict = {}
        avgDict['l'] = avgLum
        avgDict['h'] = h
        avgDict['s'] = s
        avgDict['v'] = v
        avgDict['r'] = avg_r
        avgDict['g'] = avg_g
        avgDict['b'] = avg_b
        avgList.append(avgDict)
    
    # Return the list
    return avgList

def buildOutputImage(src, dest, blockSize, hdr, alg):
    """
    Builds output image
    """
    # Create and build an output file that is the same size as the original 
    # portrait file
    outfile = Image.new("RGB", (dest.size[0], dest.size[1]))
    
    # Calculate some block sizes and counts
    srcBlockSizeX, srcBlockSizeY = calculateSrcBlockSize(src)
    srcNumBlocksX = int(src.size[0] / srcBlockSizeX)
    destNumBlocksX = int(dest.size[0] / blockSize)
    destNumBlocksY = int(dest.size[1] / blockSize)
    destBlockSizeX = blockSize
    destBlockSizeY = blockSize
        
    srcDictList = buildImageList(src, 255, (srcBlockSizeX, srcBlockSizeY))
    srcNumBlocks = len(srcDictList)
    
    destDictList = buildImageList(dest, srcNumBlocks, \
                                  (destBlockSizeX, destBlockSizeY))
        
    # Grab the number of blocks in the destination image because we'll be using 
    # this over and over
    destNumBlocks = len(destDictList)
        
    # Average together elements of the tuples based on the algorithm string
    srcList = []
    destList = []
    for i in range(srcNumBlocks):
        s_dict = srcDictList[i]
        s_sum = 0
        if ('l' in alg):
            s_sum += s_dict['l']
        if ('h' in alg):
            s_sum += s_dict['h']
        if ('s' in alg):
            s_sum += s_dict['s']
        if ('v' in alg):
            s_sum += s_dict['v']
        if ('r' in alg):
            s_sum += s_dict['r']
        if ('g' in alg):
            s_sum += s_dict['g']
        if ('b' in alg):
            s_sum += s_dict['b']
            
        s_avg = int(s_sum / len(alg))
        srcList.append((i, s_avg))
        
    for i in range(destNumBlocks):
        d_dict = destDictList[i]
        d_sum = 0
        if ('l' in alg):
            d_sum += d_dict['l']
        if ('h' in alg):
            d_sum += d_dict['h']
        if ('s' in alg):
            d_sum += d_dict['s']
        if ('v' in alg):
            d_sum += d_dict['v']
        if ('r' in alg):
            d_sum += d_dict['r']
        if ('g' in alg):
            d_sum += d_dict['g']
        if ('b' in alg):
            d_sum += d_dict['b']
        
        d_avg = int(d_sum / len(alg))   
        destList.append((i, d_avg))    
            
    # Sort based on the second element of the tuple, i.e. the hue
    srcList.sort(key=lambda tup: tup[1])
    destList.sort(key=lambda tup: tup[1])
            
    # Create a coordinate lookup list based on whether the hdr option is on or 
    # off. If off, we look up the corresponding memory block using the actual 
    # luminance value of the portrait block. This can mean that not all memory 
    # blocks are used, due to some memory list indices not existing in the list 
    # of portrait luminance values. If hdr is on, then for each portrait
    # block, a memory block will be located by scaling the index of the 
    # portrait block. Actual luminance values will not correspond to indices 
    # in the memory list in this case, but this ensures that each block in the 
    # memory list will be used.
    coordList = []                    
    if (hdr):
        scale = 1.0 / destNumBlocks * srcNumBlocks
        for i in range(destNumBlocks):
            j = int(scale * i)
            coordList.append((srcList[j][0], destList[i][0]))
           
    else:
        for i in range(destNumBlocks):
            j = int(destList[i][1])
            coordList.append((srcList[j][0], destList[i][0]))

    for i in range(destNumBlocks):
    
        # Grab the source and destination list indices
        source_idx, dest_idx = coordList[i]
        
        # Calculate the source block coordinates
        start_x = int(source_idx % srcNumBlocksX) * srcBlockSizeX
        start_y = int(source_idx / srcNumBlocksX) * srcBlockSizeY
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

def saveOutputImage(outfile, srcFile, destFile, hdr, alg, size):
    """
    Saves the output image
    """
    # Save the final image
    head, tail = os.path.split(srcFile)
    sfile, ext = os.path.splitext(tail)
    head, tail = os.path.split(destFile)
    dfile, ext = os.path.splitext(tail)
    directory = "output/"
    if not os.path.exists(directory):
        os.makedirs(directory)
    outfileName = directory + dfile + "_" + sfile + "_" + str(size) + "_" + alg
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
        s = delta / maxRGB
    else:                       # r = g = b = 0 ; s = 0, h is undefined
        s = 0.0
        h = 0.0
        return (h, s, v)

    if (minRGB == maxRGB):
        h = 0.0
    elif (r == maxRGB):
        h = (g - b) / delta            # between yellow & magenta
    elif (g == maxRGB):
        h = 2 + (b - r) / delta        # between cyan & yellow
    else:
        h = 4 + (r - g) / delta        # between magenta & cyan
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
    if (args['test']):
        algs = ['l']
    else:
        algs = buildAlgorithmList(opts)
    
    src, dest = loadImages(args['src'], args['dest'])
    
    for alg in algs:
        output = buildOutputImage(src, dest, args['blockSize'], False, alg)
        output_hdr = buildOutputImage(src, dest, args['blockSize'], True, alg)
        saveOutputImage(output, args['src'], args['dest'], False, alg, \
                        args['blockSize'])
        saveOutputImage(output_hdr, args['src'], args['dest'], True, alg, \
                        args['blockSize'])
            
    print ("Finished!")