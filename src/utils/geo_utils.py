""" Utility functions to deal with spatial data coordinates/etc """
from osgeo import osr, ogr


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


def reproject_point(x, y, from_crs_wkt, to_crs_wkt):
    """ Reproject a point to another coordinate reference system

    Args:
      x (float or int): X coordinate in `from_crs_wkt` reference system
      y (float or int): Y coordinate in `from_crs_wkt` reference system
      from_crs_wkt (str): input Coordinate Reference System as Well-Known-Text
      to_crs_wkt (str): output Coordinate Reference System as Well-Known-Text

    Returns:
      tuple: reprojected (x, y) coordinates

    """
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(x, y)

    to_srs = osr.SpatialReference()
    to_srs.ImportFromWkt(to_crs_wkt)
    from_srs = osr.SpatialReference()
    from_srs.ImportFromWkt(from_crs_wkt)

    transform = osr.CoordinateTransformation(from_srs, to_srs)
    point.Transform(transform)

    return point.GetX(), point.GetY()
