# rebuilder
Rebuilds one image using tiles from another image

This script takes a "source" image and a "destination" image as input and outputs a new destination image rebuilt using blocks from the source image. 

Type ./rebuild.py -h for usage.

This script was originally written in Python 2.5 on Mac OS X 10.6. Development is continuing under Python 2.7 on 
OS X Sierra. To run, please make sure the Pillow library is installed for your version. It can be found here:

https://pypi.python.org/pypi/Pillow

or can be installed using package managers such as Pip or Homebrew.

Feel free to read more about the project that inspired this tool here:

http://rendered-speechless.com/2014/02/past-imperfect/

### Usage

    rebuild.py src_file dest_file [-b block_size -t type -c -n -d -m med_threshold -s small_threshold]
                                 
    -b block_size      : size of tiles in destination image (default = 30)
    -t type            : create one single type (l, h, s, v, r, g, or b) or
                         combo of any number of valid types (default = lhsvrgb
                         or none if color-only option is used)
    -c                 : color-only processing
    -n                 : non-uniform block size, averages to blockSize
                         (default = False)
    -d                 : detail resolution (default = False)
    -m med_threshold   : medium size blocks (detail resolution only) will not
                         appear in areas where the color variance is below this
                         number (1-10, default = 5)
    -s small_threshold : small blocks (detail resolution only) will not appear
                         in areas where the color variance is below this number
                         (1-10, default = 8)
                       
#### Input and output
The output will be saved to the directory from which the script is called, in a folder named 'output.' The output file name will be in the form destBaseName_srcBaseName_size_type.tif. For example, if the source image is backyard.tif, and the destination image is me.tif, the block size is 30 and the type is luminance, the final output will be named me_backyard_30_l.tif and me_backyard_30_l_hdr.tif. If non-uniform blocks are used, the size will be followed by 'n,' as in me_backyard_30n_l_hdr.tif. If the detail option is also specified, the file name will appear as me_backyard_30nd_l_hdr.tif. If color-only is specified, the type character will be a 'c', as in me_backyard_30_c_hdr.tif, and will not be combined with any other types. No matter the input file formats, the output will be a TIFF. Note: Choose the best compression possible for your input files, or none at all. See Pillow docs for supported input file formats.

#### Non-uniform blocks
The sizes of the blocks are determined when the script launches, so all images produced by a single run will show the same block size pattern, but different runs will each be different from each other. Setting block size will still influence the overall resolution of the pattern, as variations are based on a percentage of the original block size.

#### Types
You can specify one single type (such as 'l') or a combination of types ('lgv'). You will get each separate type plus all combinations of the letters you include in the string. Invalid letters will be ignored. When a type is not provided, images are processed using luminance (l), hue (h), saturation (s), value (v), red (r), green (g), blue (b), and all combinations, resulting in 254 unique combinations (and output files) -- 508 including hdr versions of each.

#### Color-only
The color-only option creates blocks of solid color (the average color of the source block) rather than replacing the blocks in the destination image with the actual image blocks in the source image. If color-only is specified with any of the other types, it will only become an additional type itself. It will not be combined with the others as it requires different processing. If type is omitted and the color-only flag is on, only color processing will be done. If type is omitted and the color-only flag is off, the default types will be run (lhsvrgb).

#### Detail resolution
This image is created in three passes, with the final two passes (medium and high resolution) being dependent on the color variance of the pass before, in the areas where the new blocks would appear. Sensitivity can be adjusted using the medium and high threshold values. Adjustment of these values will provide the most pleasing variation of blocks in the final image. A higher threshold usually works best for a smaller area due to the block's lower overall pixel count, causing variance values to generally be higher. The block size in the file name will be what the user specifies, and represents the medium resolution in the final image. This number may be changed if an odd number, or too small a number, is provided.

If non-uniform is specified with detail, each pass uses its own offset tables. This can create some interesting block overlap effects.
