import os.path
from math import sqrt
from random import randint

import PIL.Image as Image

from lib import utils


class SourceImage(object):
    """
    Class that defines and processes the source image and destination images,
    each considered "sources" as opposed to "output."
    """
    def __init__(self, image, is_non_uniform, is_detail):
        """
        Init method.

        :param image: The Image object
        :param is_non_uniform: Boolean indicating non-uniformity
        :param is_detail: Boolean indicating presence of detail option
        """
        self._image = image
        self._is_non_uniform = is_non_uniform
        self._is_detail = is_detail
        self._block_size = 0
        self._block_width = 0
        self._block_height = 0
        self._num_rows = 0
        self._num_cols = 0
        self._num_blocks = 0
        self._row_list = []
        self._col_list = []
        self._avg_list = []
        self._avg_lut = []

    @classmethod
    def from_file(cls, file_name, is_non_uniform=False, is_detail=False):
        """
        Class method for creating instance using file name.

        :param file_name: String representing source image file name
        :param is_non_uniform: Boolean indicating non-uniformity
        :param is_detail: Boolean indicating presence of detail option
        :return: Class instance
        """
        image = Image.open(file_name)
        return cls(image, is_non_uniform, is_detail)

    @classmethod
    def from_image(cls, image, is_non_uniform=False, is_detail=False):
        """
        Class method for creating instance using existing open Image.

        :param image: The open Image
        :param is_non_uniform: Boolean indicating non-uniformity
        :param is_detail: Boolean indicating presence of detail option
        :return: Class instance
        """
        return cls(image, is_non_uniform, is_detail)

    def calculate_block_vars(self, user_block_size=0, width_override=0, height_override=0):
        """
        For source image: Calculates block size for src image of any size, to
        be divided evenly into 256 square-ish tiles (as close as possible). May
        be less than 256 tiles but not more.

        If user_block_size = 0, it is assumed that this is the source image.

        If user_block_size > 0, user_block_size only applies to destination image.

        For destination image: Calculates block vars based on user-input block size.
        width_override and height_override are overrides for image width and height, and
        are used for secondary destination images when detail is turned on.

        :param user_block_size: The block size
        :param width_override: Override the width using this value
        :param height_override: Override the height using this value
        :return: Nothing
        """
        width = self._image.size[0]
        height = self._image.size[1]

        if user_block_size > 0:  # if dest image

            self._block_width = user_block_size
            self._block_height = user_block_size
            if width_override > 0 and height_override > 0:
                self._num_cols = int(width_override / user_block_size)
                self._num_rows = int(height_override / user_block_size)
            else:
                self._num_cols = int(width / user_block_size)
                self._num_rows = int(height / user_block_size)

            # Build a list of offsets for block width and height. If we're
            # not using uneven blocks, we'll just set them all to 0.
            if self._is_non_uniform is True:

                # Block width will never be expanded or shrunk by more than
                # 2/3 of user block size. Create the lists one longer than
                # needed because we're looking at boundaries, not the blocks
                # themselves.
                lower = -user_block_size / 3
                upper = user_block_size / 3
                self._row_list = [randint(lower, upper) for r in range(self._num_rows + 1)]
                self._col_list = [randint(lower, upper) for c in range(self._num_cols + 1)]

                # We won't increment the first and last row or column,
                # otherwise we'll go past the edge of the image.
                self._row_list[0] = 0
                self._col_list[0] = 0
                self._row_list[self._num_rows] = 0
                self._col_list[self._num_cols] = 0

            else:

                # Create the lists one longer than needed because we're looking
                # at boundaries, not the blocks themselves
                self._row_list = [0] * (self._num_rows + 1)
                self._col_list = [0] * (self._num_cols + 1)

        else:  # if source image

            # 1024 / 512 = 2
            aspect = float(width) / float(height)
            rows = sqrt(256.0 / aspect)
            cols = aspect * rows
            rows = int(round(rows))
            cols = int(round(cols))
            self._block_width = int(width / cols)
            self._block_height = int(height / rows)
            self._num_rows = rows
            self._num_cols = cols

            # Increments aren't used on the source image. Create the lists one
            # longer because we're looking at boundaries and not the blocks
            # themselves.
            self._row_list = [0] * (self._num_rows + 1)
            self._col_list = [0] * (self._num_cols + 1)

        self._num_blocks = self._num_rows * self._num_cols
        self._block_size = self._block_width * self._block_height

    def build_average_list(self, max_value):
        """
        Builds a list of average l h s v r g b, one for each block.

        :param max_value: Maximum value used to scale the averages
        :return: Nothing
        """
        # Build the list of average block hues, values, or saturations,
        # then sort
        for i in range(self._num_blocks):

            col = int(i % self._num_cols)
            row = int(i / self._num_cols)
            start_x = col * self._block_width
            start_y = row * self._block_height
            end_x = start_x + self._block_width
            end_y = start_y + self._block_height

            # Calculate block uniformity. We have to look at the current
            # value and the next one, which correspond to the start and
            # end values respectively. The increments will be all 0's if
            # uniform blocks are used.
            start_x += self._col_list[col]
            end_x += self._col_list[col + 1]
            start_y += self._row_list[row]
            end_y += self._row_list[row + 1]
            current_block_size = (end_x - start_x) * (end_y - start_y)

            # Crop to the bounding box to create the block, then process
            bounding_box = (start_x, start_y, end_x, end_y)
            block = self._image.crop(bounding_box)
            colors = block.getcolors(current_block_size)
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
                h, s, v = utils.rgb_to_hsv(r, g, b)  # slower here but more accurate
                hsum += h * item[0]
                ssum += s * item[0]
                vsum += v * item[0]

            # Calculate full block averages here
            avg_r = float(rsum) / float(current_block_size)
            avg_g = float(gsum) / float(current_block_size)
            avg_b = float(bsum) / float(current_block_size)
            avg_l = (avg_r * 0.299) + (avg_g * 0.587) + (avg_b * 0.114)
            avg_h = float(hsum) / float(current_block_size)
            avg_s = float(ssum) / float(current_block_size)
            avg_v = float(vsum) / float(current_block_size)

            # Scale all to 0, max_value and convert to int
            avg_l = int((avg_l / 255.0) * max_value)
            avg_h = int((avg_h / 359.0) * max_value)
            avg_s = int(avg_s * max_value)
            avg_v = int((avg_v / 255.0) * max_value)
            avg_r = int((avg_r / 255.0) * max_value)
            avg_g = int((avg_g / 255.0) * max_value)
            avg_b = int((avg_b / 255.0) * max_value)

            # Calculate color variance in block, scale of 0 to 1, based on
            # actual number of unique colors in block
            variance = int(float(len(colors)) / float(current_block_size) * 10.0)

            # Save average for each alg type in a dict for the block. Also
            # save a scaled count of the number of colors present per block
            # (used for detail option).
            avg_dict = {}
            avg_dict['l'] = avg_l
            avg_dict['h'] = avg_h
            avg_dict['s'] = avg_s
            avg_dict['v'] = avg_v
            avg_dict['r'] = avg_r
            avg_dict['g'] = avg_g
            avg_dict['b'] = avg_b
            avg_dict['variance'] = variance
            self._avg_list.append(avg_dict)

    def build_average_lut(self, atype):
        """
        Builds a lookup table from calculated averages

        :param atype: A string representing the combination of algorithms
        :return: Nothing
        """
        avg_lut = []
        # Process the color-only type separately. The average of r, g and b
        # will be used to sort the list, and will be used to index it later.
        if 'c' in atype:
            for i in range(self._num_blocks):
                avg_dict = self._avg_list[i]
                r = avg_dict['r']
                g = avg_dict['g']
                b = avg_dict['b']
                avg = int((float(r) + float(g) + float(b)) / 3.0)
                variance = avg_dict['variance']

                # Store the original index, avg of r, g and b, and variance
                # together as a tuple, with the rgb values as their own tuple.
                # The avg of r, g and b will be used for sorting.
                avg_lut.append((i, avg, variance, (r, g, b)))

        else:
            for i in range(self._num_blocks):
                avg_dict = self._avg_list[i]
                alg_sum = 0.0
                variance = avg_dict['variance']
                if ('l' in atype):
                    alg_sum += avg_dict['l']
                if ('h' in atype):
                    alg_sum += avg_dict['h']
                if ('s' in atype):
                    alg_sum += avg_dict['s']
                if ('v' in atype):
                    alg_sum += avg_dict['v']
                if ('r' in atype):
                    alg_sum += avg_dict['r']
                if ('g' in atype):
                    alg_sum += avg_dict['g']
                if ('b' in atype):
                    alg_sum += avg_dict['b']

                # We store the original index and avg together as a tuple,
                # because we will need the index to calculate the coordinates
                # of where this block originally came from. Also save the color
                # variance as a third value in case we're using the detail
                # option.
                avg = int(alg_sum / len(atype))
                avg_lut.append((i, avg, variance))

        # Sort based on the second element of the tuple (the average).
        # Sorting is only necessary for the source table but it won't hurt
        # to sort the destination table as well. Since we're saving the
        # index, we always know what part of the image each block comes
        # from.
        avg_lut.sort(key=lambda tup: tup[1])

        # Assign to the internal variable so any other LUT that might have
        # been calculated will be replaced
        self._avg_lut = avg_lut

    @property
    def image(self):
        """
        Returns the Image

        :return: Image object
        """
        return self._image

    @property
    def block_size(self):
        """
        Returns block size as a tuple. If destination image, this returns
        the user-specified block size in both values, whether or not the
        blocks are meant to be uniform.

        :return: A tuple containing block width and block height
        """
        return self._block_width, self._block_height

    @property
    def rows_cols(self):
        """
        Returns number of rows and columns as a tuple.

        :return: A tuple containing the number of rows and columns
        """
        return self._num_rows, self._num_cols

    @property
    def offset_lists(self):
        """
        Returns offset lists as a tuple (used with non-uniform option).

        :return: A tuple containing the list of row offsets and list of column offsets
        """
        return self._row_list, self._col_list

    @property
    def average_lut(self):
        """
        Returns average lookup table.

        :return: Average lookup table (list).
        """
        return self._avg_lut


class OutputImage(object):
    """
    Class that creates the final output image.
    """
    def __init__(self, args, user_block_size, atype, is_hdr=False):
        """
        Init method - also creates appropriate output file name.

        :param args: Processed command-line options
        :param user_block_size: Block size
        :param atype: Algorithm type combination
        :param is_hdr: Boolean indicating whether this is an hdr image
        """
        self._atype = atype
        self._out_file = None
        self._med_threshold = args['med_threshold']
        self._small_threshold = args['small_threshold']
        self._is_non_uniform = args['is_non_uniform']
        self._is_detail = args['is_detail']
        self._user_block_size = user_block_size
        self._is_hdr = is_hdr

        # Build the output file name
        if self._is_detail is True:
            size = "{}".format(self._user_block_size / 2)
        else:
            size = "{}".format(self._user_block_size)
        head, tail = os.path.split(args['src'])
        sfile, ext = os.path.splitext(tail)
        head, tail = os.path.split(args['dest'])
        dfile, ext = os.path.splitext(tail)
        directory = "output"
        if not os.path.exists(directory):
            os.makedirs(directory)
        out_name = "{}/{}_{}_{}".format(directory, dfile, sfile, size)
        if self._is_non_uniform is True:
            out_name = "{}n".format(out_name)
        if self._is_detail is True:
            out_name = "{}d".format(out_name)
        out_name = "{}_{}".format(out_name, self._atype)
        if self._is_hdr is True:
            out_name = "{}_hdr.tif".format(out_name)
        else:
            out_name = "{}.tif".format(out_name)
        self._out_name = out_name

    def build_image(self, source_image, dest_image, dest_med=None, dest_high=None):
        """
        Builds regular and hdr output images. Additional destination images
        are used when the detail flag is specified.

        :param source_image: The source image to build from
        :param dest_image: The destination image to rebuild
        :param dest_med: Medium resolution destination image for detail option
        :param dest_high: High resolution destination image for detail option
        :return: Nothing
        """
        # Number of passes is based on whether this is a detail image.
        num_passes = 1
        if self._is_detail is True:
            num_passes = 3

        # Grab images, lookup tables and sizes
        src_img = source_image.image

        src_list = source_image.average_lut

        src_block_width, src_block_height = source_image.block_size
        src_num_rows, src_num_cols = source_image.rows_cols

        # We'll grab this again during the first pass, but we need it here to
        # calculate the output size.
        dest_num_rows, dest_num_cols = dest_image.rows_cols

        # Calculate some block sizes and counts. Even if non-uniform, the
        # number of blocks in the output will match the number in the
        # destination image.
        output_size_x = dest_num_cols * self._user_block_size
        output_size_y = dest_num_rows * self._user_block_size

        # Create and build an output file that is the size of the number of
        # rows and columns of the destination file with the given block size.
        # Should be pretty close to the original size. More cropping can occur
        # if this is a detail image because three passes need to fit in one
        # size.
        self._out_file = Image.new("RGB", (output_size_x, output_size_y))

        # Get the number of source image blocks
        src_num_blocks = len(src_list)

        # These multipliers make it possible for us to avoid an if statement
        # inside the loop. If hdr, multiply the 'scale * i' assignment by 1 and
        # the other by 0, otherwise the opposite. That way we only get one
        # value or the other.
        scale_mult = int(self._is_hdr)
        dest_mult = int(not self._is_hdr)

        # Create a list of variable dicts that will change with each pass.
        temp_list = [{}, {}, {}]
        temp_list[0]['dest_image'] = dest_image
        temp_list[1]['dest_image'] = dest_med
        temp_list[2]['dest_image'] = dest_high
        temp_list[0]['threshold'] = self._med_threshold
        temp_list[1]['threshold'] = self._small_threshold
        temp_list[2]['threshold'] = 0

        # Each pass will check against the skip list built in the previous pass
        last_skip_list = None

        for p in range(num_passes):

            current_dest_image = temp_list[p]['dest_image']
            current_threshold = temp_list[p]['threshold']

            src_block = None

            # Get increment lists from the destination image
            row_list, col_list = current_dest_image.offset_lists
            current_row_list = row_list
            current_col_list = col_list

            # Save rows and columns (only columns is used)
            rows, cols = current_dest_image.rows_cols
            current_cols = cols

            # Get the destination lookup table
            current_dest_lut = current_dest_image.average_lut
            current_num_blocks = len(current_dest_lut)

            # Create a coordinate lookup list based on whether the hdr option
            # is on or off. If off, we look up the corresponding memory block
            # using the actual luminance value of the portrait block. This can
            # mean that not all memory blocks are used, due to some memory list
            # indices not existing in the list of portrait luminance values. If
            # hdr is on, then for each portrait block, a memory block will be
            # located by scaling the index of the portrait block. Actual
            # luminance values will not correspond to indices in the memory
            # list in this case, but this ensures that each block in the memory
            # list will be used.
            current_scale = 1.0 / current_num_blocks * src_num_blocks

            # Create a list of indices where the color variance is 0. This will
            # be the blocks we skip in the detail passes, if we're using them.
            skip_list = []

            # Add the block size for this pass
            current_block_size = self._user_block_size / (2 ** p)

            for i in range(current_num_blocks):
                j = (int(current_scale * i) * scale_mult) + \
                    (int(current_dest_lut[i][1]) * dest_mult)

                # Grab the source and destination list indices
                src_idx = src_list[j][0]
                dest_idx = current_dest_lut[i][0]

                # Grab the color variance of the block. If it's below the
                # threshold we'll save it to the list to be skipped in future
                # passes.
                variance = current_dest_lut[i][2]

                # PASS > 0
                # Work backwards to find the index of the larger block that
                # contains this smaller one. Division by 0 is not an issue
                # because this won't run on pass 0
                if last_skip_list is not None:
                    y = dest_idx / (current_cols * (2))
                    x = (dest_idx % current_cols) / (2)
                    outeridx = (y * (current_cols / 2)) + x

                    if outeridx in last_skip_list:
                        skip_list.append(dest_idx)
                        continue

                if variance < current_threshold:
                    skip_list.append(dest_idx)

                # For the color-only type, we'll fill the destination block
                # with a solid color. For all others, we'll paste a block from
                # the source image.
                if 'c' not in self._atype:

                    # Calculate the source block bounding box (no size
                    # variations)
                    start_x = int(src_idx % src_num_cols) * src_block_width
                    start_y = int(src_idx / src_num_cols) * src_block_height
                    end_x = start_x + src_block_width
                    end_y = start_y + src_block_height

                    # Grab the source image blocks
                    src_block = src_img.crop((start_x, start_y, end_x, end_y))

                    # Randomly determine whether this block will be flipped
                    # and/or rotated
                    flip = randint(0, 2)
                    rotate = randint(0, 3)
                    if (flip > 0):
                        src_block = src_block.transpose(flip - 1)
                    if (rotate > 0):
                        src_block = src_block.transpose(rotate - 1)

                # Calculate destination block position and size
                col = int(dest_idx % current_cols)
                row = int(dest_idx / current_cols)
                start_x = col * current_block_size
                start_y = row * current_block_size
                end_x = start_x + current_block_size
                end_y = start_y + current_block_size

                # Calculate block uniformity. We have to look at the current
                # value and the next one, which correspond to the start and
                # end values respectively. The offsets will be all 0's if
                # uniform blocks are used.
                start_x += current_col_list[col]
                end_x += current_col_list[col + 1]
                start_y += current_row_list[row]
                end_y += current_row_list[row + 1]

                # Calculate the block's dimensions. Will be different each time
                # if non-uniform is used.
                dest_block_width = end_x - start_x
                dest_block_height = end_y - start_y

                if 'c' in self._atype:
                    rgb = src_list[j][3]
                    src_block = Image.new("RGB",
                                          (dest_block_width, dest_block_height),
                                          rgb)

                else:

                    # If the dest block size is not equal to the source block
                    # size, resize the source block to be the same size as the
                    # dest block
                    if (src_block_width != dest_block_width) or (src_block_height != dest_block_height):
                        src_block = src_block.resize((dest_block_width, dest_block_height))

                # Paste the memory block into the correct coordinates of
                # the output file
                self._out_file.paste(src_block, (start_x, start_y))

            last_skip_list = skip_list

    def save_image(self):
        """
        Saves the output image to disk.

        :return: Nothing
        """
        self._out_file.save(self._out_name, "TIFF")
        print "Saved {}".format(self._out_name)
