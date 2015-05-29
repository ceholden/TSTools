""" Utility functions to deal with spatial data coordinates/etc """


def point2pixel(x, y, gt):
    """ Convert a coordinate x/y pair to pixel coordinates

    Notes:
      Does not handle images that aren't north up (gt[2] or gt[4] are nonzero)

    Args:
      x (float): X coordinate (e.g., longitude)
      y (float): Y coordinate (e.g., latitude)
      gt (iterable): geotransform containing 6 coefficients of affine transform

    Returns:
      tuple (int, int): column and row pixel coordinates for given x/y

    """
    px = int((x - gt[0]) / gt[1])
    py = int((y - gt[3]) / gt[5])

    return px, py
