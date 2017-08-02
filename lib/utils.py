import itertools


def build_algorithm_list(opts):
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
    
def rgb_to_hsv(r, g, b):
    """
    Converts RGB to HSV
    """
    min_rgb = min( r, g, b )
    max_rgb = max( r, g, b )
    v = float(max_rgb)
    delta = max_rgb - min_rgb
    
    if (max_rgb > 0):
        s = float(delta) / float(max_rgb)
    else:                       # r = g = b = 0 ; s = 0, h is undefined
        s = 0.0
        h = 0.0
        return h, s, v

    if min_rgb == max_rgb:
        h = 0.0
    elif r == max_rgb:
        h = (g - b) / float(delta)            # between yellow & magenta
    elif g == max_rgb:
        h = 2 + (b - r) / float(delta)        # between cyan & yellow
    else:
        h = 4 + (r - g) / float(delta)        # between magenta & cyan
    h *= 60.0                                 # degrees
    if h < 0.0:
        h += 360.0
        
    return h, s, v