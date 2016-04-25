from PIL import Image
import os.path
from random import randint
from math import sqrt
import itertools

class SourceImage(object):
    
    def __init__(self, filename):
        """
        Init method
        """
        self.image = Image.open(filename)
        self.blockSize = 0
        self.blockSizeX = 0
        self.blockSizeY = 0
        self.numRows = 0
        self.numCols = 0
        self.numBlocks = 0
        self.avgList = []
        self.avgLUT = []
        
    def calculateBlockVars(self, userBlockSize=0, isNonUniform=False):
        """
        For source image: Calculates block size for src image of any size, to 
        be divided evenly into 256 square-ish tiles (as close as possible). May 
        be less than 256 tiles but not more. 
        If userBlockSize = 0, it is assumed that this is the source image.
        If userBlockSize > 0, variable only applies to destination image. 
        For dest image: Calculates block vars based on user-input block size.
        """
        sizeX = self.image.size[0]
        sizeY = self.image.size[1]
        
        if userBlockSize > 0:  # if dest image
            self.blockSizeX = userBlockSize
            self.blockSizeY = userBlockSize
            self.numCols = int(sizeX / userBlockSize)
            self.numRows = int(sizeY / userBlockSize)

        else: # if source image
            # 1024 / 512 = 2
            aspect = float(sizeX) / float(sizeY)
            rows = sqrt(256.0 / aspect)
            cols = aspect * rows
            rows = int(round(rows))
            cols = int(round(cols))
            self.blockSizeX = int(sizeX / cols)
            self.blockSizeY = int(sizeY / rows)
            self.numRows = rows
            self.numCols = cols
                 
        self.numBlocks = self.numRows * self.numCols
        self.blockSize = self.blockSizeX * self.blockSizeY
        
    def buildAverageList(self, maxValue, isNonUniform=False):
        """
        Builds a list of average l h s v r g b, one for each block.
        """
        # Build the list of average block hues, values, or saturations, 
        # then sort
        for i in range(self.numBlocks):
            start_x = int(i % self.numCols) * self.blockSizeX
            start_y = int(i / self.numCols) * self.blockSizeY
            end_x = start_x + self.blockSizeX
            end_y = start_y + self.blockSizeY
            boundingBox = (start_x, start_y, end_x, end_y)
            block = self.image.crop(boundingBox)
            colors = block.getcolors(self.blockSize)
            rsum, gsum, bsum = 0, 0, 0
            hsum, ssum, vsum = 0.0, 0.0, 0.0
            # Get per-pixel values and keep running total for each alg type
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
            # Calculate full block averages here
            avg_r = float(rsum) / float(self.blockSize)
            avg_g = float(gsum) / float(self.blockSize)
            avg_b = float(bsum) / float(self.blockSize)
            avg_l = (avg_r * 0.299) + (avg_g * 0.587) + (avg_b * 0.114)
            avg_h = float(hsum) / float(self.blockSize)
            avg_s = float(ssum) / float(self.blockSize)
            avg_v = float(vsum) / float(self.blockSize)
                        
            # Scale all to 0, maxValue and convert to int
            avg_l = int((avg_l / 255.0) * maxValue)
            avg_h = int((avg_h / 359.0) * maxValue)
            avg_s = int(avg_s * maxValue)
            avg_v = int((avg_v / 255.0) * maxValue)
            avg_r = int((avg_r / 255.0) * maxValue)
            avg_g = int((avg_g / 255.0) * maxValue)
            avg_b = int((avg_b / 255.0) * maxValue)
            
            # Save average for each alg type in a dict for the block
            avgDict = {}
            avgDict['l'] = avg_l
            avgDict['h'] = avg_h
            avgDict['s'] = avg_s
            avgDict['v'] = avg_v
            avgDict['r'] = avg_r
            avgDict['g'] = avg_g
            avgDict['b'] = avg_b
            self.avgList.append(avgDict)
            
    def buildAverageLUT(self, atype):
        """
        Builds a lookup table from calculated averages
        """
        avgLUT = []
        for i in range(self.numBlocks):
            avgDict = self.avgList[i]
            algSum = 0.0
            if ('l' in atype):
                algSum += avgDict['l']
            if ('h' in atype):
                algSum += avgDict['h']
            if ('s' in atype):
                algSum += avgDict['s']
            if ('v' in atype):
                algSum += avgDict['v']
            if ('r' in atype):
                algSum += avgDict['r']
            if ('g' in atype):
                algSum += avgDict['g']
            if ('b' in atype):
                algSum += avgDict['b']
            
            # We store the original index and avg together as a tuple, 
            # because we will need the index to calculate the coordinates of 
            # where this block originally came from
            avg = int(algSum / len(atype))   
            avgLUT.append((i, avg))
            
        # Sort based on the second element of the tuple (the average). Sorting
        # is only necessary for the source table but it won't hurt to sort
        # the destination table as well. Since we're saving the index, we
        # always know what part of the image each block comes from.
        avgLUT.sort(key=lambda tup: tup[1])
        
        # Assign to the internal variable so any other LUT that might have
        # been calculated will be replaced
        self.avgLUT = avgLUT
        
    def getImage(self):
        """ 
        Returns image 
        """
        return self.image
    
    def getBlockSize(self):
        """ 
        Returns block size as a tuple
        """
        return (self.blockSizeX, self.blockSizeY)
    
    def getRowsCols(self):
        """
        Returns number of rows and columns as a tuple
        """
        return (self.numRows, self.numCols)
    
    def getAverageLUT(self):
        """ 
        Returns average lookup table
        """
        return self.avgLUT
                    
class OutputImage(object):
    
    def __init__(self, args, atype, hdr=False):
        """
        Init method - also creates appropriate output file name.
        """
        self.atype = atype
        self.outName = ''
        self.outfile = None
        self.isNonUniform = args['isNonUniform']
        self.userBlockSize = args['blockSize']
        self.hdr = hdr
        # Build file names for later
        srcFile = args['src']
        destFile = args['dest']
        size = str(str(self.userBlockSize))
        head, tail = os.path.split(srcFile)
        sfile, ext = os.path.splitext(tail)
        head, tail = os.path.split(destFile)
        dfile, ext = os.path.splitext(tail)
        directory = "output/"
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.outName = directory + dfile + "_" + sfile + "_" + size
        if self.isNonUniform:
            self.outName = self.outName + 'n'
        self.outName = self.outName + "_" + self.atype
        if self.hdr:
            self.outName = self.outName + '_hdr.tif'
        else:
            self.outName = self.outName + '.tif'
        
    def buildImage(self, sourceImage, destImage):
        """
        Builds regular and hdr output images
        """
        # Grab images, lookup tables and sizes
        srcImg = sourceImage.getImage()
        
        srcList = sourceImage.getAverageLUT()
        destList = destImage.getAverageLUT()
        
        srcBlockSizeX, srcBlockSizeY = sourceImage.getBlockSize()
        srcNumRows, srcNumCols = sourceImage.getRowsCols()
        destNumRows, destNumCols = destImage.getRowsCols()       
        
        # Calculate some block sizes and counts. Even if non-uniform, the 
        # number of blocks in the output will match the number in the
        # destination image.
        destBlockSizeX = self.userBlockSize
        destBlockSizeY = self.userBlockSize
        outputSizeX = destNumCols * self.userBlockSize
        outputSizeY = destNumRows * self.userBlockSize
                
        # Create and build an output file that is the size of the number of rows
        # and columns of the destination file with the given block size. Should 
        # be pretty close to the original size.
        self.outfile = Image.new("RGB", (outputSizeX, outputSizeY))
            
        srcNumBlocks = len(srcList)
        destNumBlocks = len(destList)
                    
        # Create a coordinate lookup list based on whether the hdr option is on 
        # or off. If off, we look up the corresponding memory block using the 
        # actual luminance value of the portrait block. This can mean that not 
        # all memory blocks are used, due to some memory list indices not 
        # existing in the list of portrait luminance values. If hdr is on, then 
        # for each portrait block, a memory block will be located by scaling 
        # the index of the portrait block. Actual luminance values will not 
        # correspond to indices in the memory list in this case, but this 
        # ensures that each block in the memory list will be used.
        scale = 1.0 / destNumBlocks * srcNumBlocks
        
        # These multipliers make it possible for us to avoid an if statement 
        # inside the loop. If hdr, multiply the 'scale * i' assignment by 1 and
        # the other by 0, otherwise the opposite. That way we only get one value
        # or the other.
        scale_mult = int(self.hdr)
        dest_mult = int(not self.hdr)
        
        for i in range(destNumBlocks):
            j = (int(scale * i) * scale_mult) + (int(destList[i][1]) * dest_mult)
            
            # Grab the source and destination list indices
            src_idx = srcList[j][0]
            dest_idx = destList[i][0]
            
            start_x = int(src_idx % srcNumCols) * srcBlockSizeX
            start_y = int(src_idx / srcNumCols) * srcBlockSizeY
            end_x = start_x + srcBlockSizeX
            end_y = start_y + srcBlockSizeY
            
            # Grab the source image blocks
            srcBlock = srcImg.crop((start_x, start_y, end_x, end_y))
            
            # Randomly determine whether this block will be flipped and/or 
            # rotated
            flip = randint(0, 2)
            rotate = randint(0, 3)
            if (flip > 0):
                srcBlock = srcBlock.transpose(flip-1)
            if (rotate > 0):
                srcBlock = srcBlock.transpose(rotate-1)
                
            # If the dest block size is not equal to the source block size, 
            # resize the source block to be the same size as the dest block
            if (destBlockSizeX * destBlockSizeY != 
                srcBlockSizeX * srcBlockSizeY):
                srcBlock = srcBlock.resize((destBlockSizeX, destBlockSizeY))
                
            # Calculate the coordinates of the dest block to be replaced
            start_x = (dest_idx % destNumCols) * destBlockSizeX
            start_y = (dest_idx / destNumCols) * destBlockSizeY
            
            # Paste the memory block into the correct coordinates of the output 
            # file
            self.outfile.paste(srcBlock, (start_x, start_y))
            
    def saveImage(self):
        """
        Saves the output image
        """
        self.outfile.save(self.outName, "TIFF")
        print("Saved " + self.outName)
            
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
    
def RGBtoHSV(r, g, b):
    """
    Converts RGB to HSV
    """
    minRGB = min( r, g, b )
    maxRGB = max( r, g, b )
    v = float(maxRGB)
    delta = maxRGB - minRGB
    
    if (maxRGB > 0):
        s = float(delta) / float(maxRGB)
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
    h *= 60.0                                 # degrees
    if (h < 0.0):  
        h += 360.0
        
    return (h, s, v)