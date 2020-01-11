#! /usr/bin/python

"""
rebuild.py by Amy Tucker

This rebuilds a "destination" image using the tiles of a "source" image. It 
accepts two images as input. See README.md for detailed usage instructions.
"""

import argparse
import os.path
from sys import stderr

from lib import utils
from lib.image import SourceImage, OutputImage


def process_args():
    """
    Processes command line arguments

    :return: A dict containing the processed options
    """
    rebld_args = {}

    parser = argparse.ArgumentParser(description='Rebuilds one image from another image')

    parser.add_argument("source_image",
                        help="Source image file")
    parser.add_argument("dest_image",
                        help="Destination image file (the image to rebuild using source_image)")
    parser.add_argument("-b",
                        action="store",
                        default="30",
                        type=int,
                        dest="block_size",
                        help="Block size in pixels (default = 30)")
    parser.add_argument("-t",
                        action="store",
                        default="",
                        dest="type",
                        help="Type (l, h, s, v, r, g, b or combination)")
    parser.add_argument("-c",
                        action="store_true",
                        default="False",
                        dest="do_color",
                        help="Color-only processing")
    parser.add_argument("-n",
                        action="store_true",
                        default=False,
                        dest="is_non_uniform",
                        help="Make block size non-uniform")
    parser.add_argument("-d",
                        action="store_true",
                        default=False,
                        dest="is_detail",
                        help="Use detail resolution")
    parser.add_argument("-m",
                        action="store",
                        default=5,
                        type=int,
                        dest="med_threshold",
                        help="Medium res color variance threshold (1-10, default = 5)")
    parser.add_argument("-s",
                        action="store",
                        default=8,
                        type=int,
                        dest="small_threshold",
                        help="High res color variance threshold (1-10, default = 8)")

    options = parser.parse_args()

    # Create some temporary variables to validate before assigning to the
    # args dict later
    temp_block_size = options.block_size
    temp_type = options.type
    temp_med_threshold = options.med_threshold
    temp_small_threshold = options.small_threshold

    # Check for valid files. Pillow will check that they're valid images.
    if not os.path.isfile(options.source_image):
        raise SystemExit("ERROR: Invalid source file '{}'.\n".format(options.source_image))

    if not os.path.isfile(options.dest_image):
        raise SystemExit("ERROR: Invalid destination file '{}'.\n".format(options.dest_image))

    # Make sure we have a workable block size
    if options.is_detail is True:
        if temp_block_size < 8:
            stderr.write("WARNING: Block size too small for detail option. Clamped to 8.\n")
            temp_block_size = 8
        elif temp_block_size % 2 != 0:
            temp_block_size -= 1
            stderr.write("WARNING: Even block size needed for detail. Block size changed to '{}'.\n".format(
                temp_block_size))
    elif temp_block_size < 4:
        temp_block_size = 4
        stderr.write("WARNING: Block size too small. Clamped to '{}'.\n".format(temp_block_size))

    # Check for duplicate, invalid and extra chars in type string
    type_dict = {}
    for t in temp_type:
        if t in 'lhsvrgb':
            if type_dict.has_key(t):
                stderr.write("WARNING: Duplicate type '{}' ignored.\n".format(t))
            else:
                type_dict[t] = 1
        else:
            stderr.write("WARNING: Invalid type '{}' ignored.\n".format(t))

    # Check threshold values
    if options.is_detail is True:
        if temp_med_threshold < 1 or temp_med_threshold > 10:
            temp_med_threshold = 5
            stderr.write("WARNING: Medium threshold out of 1-10 range, set to '{}'.\n".format(temp_med_threshold))

        if temp_small_threshold < 1 or temp_small_threshold > 10:
            temp_small_threshold = 8
            stderr.write("WARNING: Small threshold out of 1-10 range, set to '{}'.\n".format(temp_small_threshold))


    # Set filenames and additional options
    rebld_args['src'] = options.source_image
    rebld_args['dest'] = options.dest_image

    rebld_args['block_size'] = temp_block_size
    rebld_args['type'] = type_dict.keys()
    rebld_args['do_color'] = options.do_color
    rebld_args['is_non_uniform'] = options.is_non_uniform
    rebld_args['is_detail'] = options.is_detail
    rebld_args['med_threshold'] = temp_med_threshold
    rebld_args['small_threshold'] = temp_small_threshold

    return rebld_args
    
    
if __name__ == '__main__':

    # Process arguments
    args = process_args()
    
    # Set up some variables
    source_name = args['src']
    dest_name = args['dest']
    do_color = args['do_color']
    is_non_uniform = args['is_non_uniform']
    is_detail = args['is_detail']
    user_block_size = args['block_size']
    user_block_size_med = 0
    user_block_size_high = 0
    
    # Build the algorithm list
    opts = 'lhsvrgb'
    if len(args['type']) == 1:
        algs = args['type'] 
    elif len(args['type']) > 1:
        algs = utils.build_algorithm_list(args['type'])
    else:
        # If color-only is specified and type is not given, this is allowed.
        # But if color-only is off and type is not specified, load all the 
        # types by default.
        if do_color is True:
            algs = []
        else:
            algs = utils.build_algorithm_list(opts)
    
    # Two extra destination images will be used if detail flag is set
    dest_med = None
    dest_high = None
    
    # If detail resolution is set, we'll complete the same tasks for two 
    # additional destination images and manipulate the block size for all.
    if is_detail is True:
        
        # We'll need additional block sizes for the other two images
        # we'll pull from.
        user_block_size_high = user_block_size / 2
        user_block_size_med = user_block_size
        user_block_size = user_block_size * 2
        
    # Create the source class instances and open the images
    source = SourceImage.from_file(source_name)
    dest = SourceImage.from_file(dest_name, is_non_uniform, is_detail)
    
    # Calculate internal data based on whether this is a source or
    # destination image. Passing the user-entered blockSize will flag the
    # image as a destination image.
    print "Calculating blocks..."
    source.calculate_block_vars()
    dest.calculate_block_vars(user_block_size)
    
    # Get the number of blocks in the source image. We'll use this to
    # send a max_value when we build the average list.
    src_rows, src_cols = source.rows_cols
    max_value = (src_rows * src_cols) - 1
    
    # Average lists are straightforward
    print "Calculating averages..."
    source.build_average_list(max_value)
    dest.build_average_list(max_value)
        
    # Repeat the above process for the additional detail images
    if is_detail is True:

        # Create the additional image instances. We'll use the actual image
        # from the first destination image created so we don't open the same
        # file three times.
        dest_med = SourceImage.from_image(dest.image, is_non_uniform, is_detail)
        dest_high = SourceImage.from_image(dest.image, is_non_uniform, is_detail)
        
        # We need to sync up the final image size with the main destination 
        # image. We'll use width and height overrides when calculating blocks 
        # in the additional images to make sure everything is the same size.
        dest_rows, dest_cols = dest.rows_cols
        width = dest_cols * user_block_size
        height = dest_rows * user_block_size
        
        print "Calculating blocks for detail layers..."
        dest_med.calculate_block_vars(user_block_size_med, width, height)
        dest_high.calculate_block_vars(user_block_size_high, width, height)
    
        # Build the average lists for each, using the maxValue calculated from
        # the common source image number of blocks
        print "Calculating averages for detail layers..."
        dest_med.build_average_list(max_value)
        dest_high.build_average_list(max_value)
            
    # Iterate through the image types and combinations we're processing and
    # create output images
    if len(algs) > 0:
        print "Processing types and combinations..."
        
    for atype in algs:
        
        # Create the output based on the current algorithm
        output = OutputImage(args, user_block_size, atype)
        output_hdr = OutputImage(args, user_block_size, atype, True)
        
        # Lookups change for each algorithm
        source.build_average_lut(atype)
        dest.build_average_lut(atype)
        
        # Build hdr and non-hdr versions
        if is_detail is True:
            dest_med.build_average_lut(atype)
            dest_high.build_average_lut(atype)
            output.build_image(source, dest, dest_med, dest_high)
            output_hdr.build_image(source, dest, dest_med, dest_high)
        else:
            output.build_image(source, dest)
            output_hdr.build_image(source, dest)
                
        # Save the output images
        output.save_image()
        output_hdr.save_image()
        
    # Do the color-only processing, if requested
    if do_color is True:
        
        print "Processing color-only option..."
        
        # Create the output for the color images
        output = OutputImage(args, user_block_size, 'c')
        output_hdr = OutputImage(args, user_block_size, 'c', True)
        
        # Lookups are a little different for this type
        source.build_average_lut('c')
        dest.build_average_lut('c')
        
        # Build hdr and non-hdr versions
        if is_detail is True:
            dest_med.build_average_lut('c')
            dest_high.build_average_lut('c')
            output.build_image(source, dest, dest_med, dest_high)
            output_hdr.build_image(source, dest, dest_med, dest_high)
        else:
            output.build_image(source, dest)
            output_hdr.build_image(source, dest)
        
        # Save the output images
        output.save_image()
        output_hdr.save_image()
                    
    print "Finished!"
