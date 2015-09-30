""" Utility functions to deal with spatial data coordinates/etc
"""
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


def pixel_geometry(gt, px, py):
    """ Return an instance of ogr.Geometry for a pixel at given X/Y coordinate

    Args:
      gt (list): geotransform of raster
      px (int): X (column) pixel coordinate
      py (int): Y (row) pixel coordinate

    Returns:
      ogr.Geometry: OGR geometry of pixel at px/py

    """
    ulx = (gt[0] + px * gt[1] + py * gt[2])
    uly = (gt[3] + px * gt[4] + py * gt[5])

    geom = ogr.Geometry(ogr.wkbPolygon)
    ring = ogr.Geometry(type=ogr.wkbLinearRing)

    ring.AddPoint(ulx, uly)  # upper left
    ring.AddPoint(ulx + gt[1], uly)  # upper right
    ring.AddPoint(ulx + gt[1], uly + gt[5])  # lower right
    ring.AddPoint(ulx, uly + gt[5])  # lower left
    ring.AddPoint(ulx, uly)  # upper left

    geom.AddGeometry(ring)

    return geom


def merge_geometries(geom_wkts, crs_wkts):
    """ Combine geometries into a wkbMultiPolygon

    Note that if geometries are in differnet CRS, geometries will be
    reprojected to the CRS of the first geometry.

    Args:
      geom_wkts (list): list of geometries as WKT
      crs_wkts (list): list of coordinate reference systems as WKT

    Returns:
      tuple: multipolygon ogr.Geometry and geometry CRS as WKT

    """
    crs = []
    for wkt in crs_wkts:
        _crs = osr.SpatialReference()
        _crs.ImportFromWkt(wkt)
        crs.append(_crs)

    geom = ogr.Geometry(ogr.wkbMultiPolygon)
    for i, (_geom_wkt, _crs) in enumerate(zip(geom_wkts, crs)):
        _geom = ogr.CreateGeometryFromWkt(_geom_wkt)
        if i != 0:
            coord_transform = osr.CoordinateTransformation(_crs, crs[0])
            _geom.Transform(coord_transform)
        geom.AddGeometry(_geom)

    crs_wkt = crs[0].ExportToWkt()
    return geom, crs_wkt
