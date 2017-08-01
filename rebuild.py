#! /usr/bin/python

"""
rebuild.py by Amy Tucker

This rebuilds a "destination" image using the tiles of a "source" image. It 
accepts two images as input. See README.md for detailed usage instructions.
"""

import rebuilderutils as rutils
from optparse import OptionParser
from sys import stderr, argv
import os.path

def process_args():
    """
    Processes command line arguments
    """
    rebld_args = {}
        
    usage = "Usage: %prog src_image dest_image [options]"
    p = OptionParser(usage=usage)
    p.add_option("-b", action="store", dest="block_size",
                 help="Block size in pixels (default = 30)")
    p.add_option("-t", action="store", dest="type", 
                 help="Type (l, h, s, v, r, g, b or combination - optional)")
    p.add_option("-c", action="store_true", dest="do_color",
                 help="Color-only processing - optional")
    p.add_option("-n", action="store_true", dest="is_non_uniform",
                 help="Make block size non-uniform - optional")
    p.add_option("-d", action="store_true", dest="is_detail",
                 help="Use detail resolution - optional")
    p.add_option("-m", action="store", dest="med_threshold",
                 help="Medium res color variance threshold (1-10, default = 5)")
    p.add_option("-s", action="store", dest="small_threshold",
                 help="High res color variance threshold (1-10, default = 8)")
    
    p.set_defaults(block_size = 30)
    p.set_defaults(type = '')
    p.set_defaults(do_color = False)
    p.set_defaults(is_non_uniform = False)
    p.set_defaults(is_detail = False)
    p.set_defaults(med_threshold = 5)
    p.set_defaults(small_threshold = 8)
    
    opts, args = p.parse_args()
    
    # Create some temporary variables to validate before assigning to the 
    # args dict later
    temp_block_size = int(opts.block_size)
    temp_type = opts.type
    temp_do_color = opts.do_color
    temp_is_non_uniform = opts.is_non_uniform
    temp_is_detail = opts.is_detail
    temp_med_threshold = int(opts.med_threshold)
    temp_small_threshold = int(opts.small_threshold)
    
    # Check that we have two file names
    if (len(args) != 2):
        stderr.write("Wrong number of arguments\n")
        stderr.write("Usage: %s src_image dest_image " % argv[0])
        stderr.write("[-b block_size -t type -n \n")
        stderr.write("       -d -m med_threshold -s small_threshold]\n")
        raise SystemExit(1)
    
    # Check for valid files. PIL will check that they're valid images.
    if (not os.path.isfile(args[0])):
        stderr.write("Invalid source file\n")
        stderr.write("Usage: %s src_image dest_image " % argv[0])
        stderr.write("[-b block_size -t type -n \n")
        stderr.write("       -d -m med_threshold -s small_threshold]\n")
        raise SystemExit(1)
    
    if (not os.path.isfile(args[1])):
        stderr.write("Invalid destination file\n")
        stderr.write("Usage: %s src_image dest_image " % argv[0])
        stderr.write("[-b block_size -t type -n \n")
        stderr.write("       -d -m med_threshold -s small_threshold]\n")
        raise SystemExit(1)
    
    # Make sure we have a workable block size
    if temp_block_size < 8 and temp_is_detail is True:
        stderr.write("Block size too small for detail option. Clamped to 8.\n")
        temp_block_size = 8
    elif temp_block_size < 4:
        stderr.write("Block size too small. Clamped to 4.\n")
        temp_block_size = 4
    
    # Check for duplicate, invalid and extra chars in type string
    type_dict = {}
    for t in temp_type:
        if t in 'lhsvrgb':
            if type_dict.has_key(t):
                stderr.write("Duplicate type %s ignored\n" % t)
            else:
                type_dict[t] = 1
        else:
            stderr.write("Invalid type %s ignored\n" % t)
    
    # Check threshold values
    if temp_is_detail is True:
        if temp_med_threshold < 1 or temp_med_threshold > 10:
            stderr.write("Medium threshold out of 1-10 range, set to 5.\n")
            opts.temp_med_threshold = 5
        if temp_small_threshold < 1 or temp_small_threshold > 10:
            stderr.write("Small threshold out of 1-10 range, set to 8.\n")
            temp_small_threshold = 8
    
    # Set filenames and additional options
    rebld_args['src'] = args[0]
    rebld_args['dest'] = args[1]
    
    rebld_args['block_size'] = temp_block_size
    rebld_args['type'] = type_dict.keys()
    rebld_args['do_color'] = temp_do_color
    rebld_args['is_non_uniform'] = temp_is_non_uniform
    rebld_args['is_detail'] = temp_is_detail
    rebld_args['med_threshold'] = temp_med_threshold
    rebld_args['small_threshold'] = temp_small_threshold
    
    return (rebld_args)
    
    
if __name__ == '__main__':
    """ 
    Main function
    """
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
    if (len(args['type']) == 1):
        algs = args['type'] 
    elif (len(args['type']) > 1):
        algs = rutils.build_algorithm_list(args['type'])
    else:
        # If color-only is specified and type is not given, this is allowed.
        # But if color-only is off and type is not specified, load all the 
        # types by default.
        if do_color:
            algs = []
        else:
            algs = rutils.build_algorithm_list(opts)
    
    # Two extra destination images will be used if detail flag is set
    dest_med = None
    dest_high = None
    
    # If detail resolution is set, we'll complete the same tasks for two 
    # additional destination images and manipulate the block size for all.
    if is_detail:
        
        # We need to make sure our block size is an even number before using 
        # it. Probably safer to subtract 1 than add. We'll also need additional
        # block sizes for the other two images we'll pull from.
        if user_block_size % 2 != 0:
            user_block_size -= 1
            stderr.write("Even block size needed when detail flag is set.\n")
            stderr.write("Block size changed to %d.\n" % user_block_size)
        user_block_size_high = user_block_size / 2
        user_block_size_med = user_block_size
        user_block_size = user_block_size * 2
        
    # Create the source class instances and open the images
    source = rutils.SourceImage.from_file(source_name)
    dest = rutils.SourceImage.from_file(dest_name, is_non_uniform, is_detail)
    
    # Calculate internal data based on whether this is a source or
    # destination image. Passing the user-entered blockSize will flag the
    # image as a destination image.
    print "Calculating blocks..."
    source.calculate_block_vars()
    dest.calculate_block_vars(user_block_size)
    
    # Get the number of blocks in the source image. We'll use this to
    # send a maxValue when we build the average list.
    src_rows, src_cols = source.rows_cols
    max_value = (src_rows * src_cols) - 1
    
    # Average lists are straightforward
    print "Calculating averages..."
    source.build_average_list(max_value)
    dest.build_average_list(max_value)
        
    # Repeat the above process for the additional detail images
    if is_detail:

        # Create the additional image instances. We'll use the actual image
        # from the first destination image created so we don't open the same
        # file three times.
        dest_image = dest.getImage()
        dest_med = rutils.SourceImage.from_image(dest_image, is_non_uniform, is_detail)
        dest_high = rutils.SourceImage.from_image(dest_image, is_non_uniform, is_detail)
        
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
        output = rutils.OutputImage(args, user_block_size, atype)
        output_hdr = rutils.OutputImage(args, user_block_size, atype, True)
        
        # Lookups change for each algorithm
        source.build_average_lut(atype)
        dest.build_average_lut(atype)
        
        # Build hdr and non-hdr versions
        if is_detail:
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
    if do_color:
        
        print "Processing color-only option..."
        
        # Create the output for the color images
        output = rutils.OutputImage(args, user_block_size, 'c')
        output_hdr = rutils.OutputImage(args, user_block_size, 'c', True)
        
        # Lookups are a little different for this type
        source.build_average_lut('c')
        dest.build_average_lut('c')
        
        # Build hdr and non-hdr versions
        if is_detail:
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