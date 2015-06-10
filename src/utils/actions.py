""" Miscellaneous actions related to plugin
"""
import logging

import qgis.core

from .. import settings
from ..logger import qgis_log
from ..ts_driver.ts_manager import tsm

logger = logging.getLogger('tstools')


def apply_symbology(rlayers=None):
    """ Apply raster symbology to all raster layers in timeseries

    Args:
      rlayers (list or QgsRasterLayer, optional): list of QgsRasterLayer, or
        a single QgsRasterLayer. If None, apply symbology to all tracked
        raster layers

    """
    if not settings.symbol_control:
        logger.debug('Not applying symbology -- control turned off')
        return

    if not rlayers:
        rlayers = settings.image_layers
    elif not isinstance(rlayers, list):
        rlayers = [rlayers]

    for rlayer in rlayers:
        logger.debug('Applying symbology to raster layer: {r} ({m})'.format(
            r=rlayer.id(), m=hex(id(rlayer))))
        # Find corresponding Series
        i_series = None
        for i, series in enumerate(tsm.ts.series):
            if rlayer.source() in series.images['path']:
                i_series = i
                break
        if i_series is None:
            logger.warning('Could not match raster layer {r} to a'
                           ' Series'.format(r=rlayer.id()))
            continue

        # Apply symbology
        r_band = settings.symbol[i_series]['band_red']
        g_band = settings.symbol[i_series]['band_green']
        b_band = settings.symbol[i_series]['band_blue']

        # Contrast enhancements
        r_ce = qgis.core.QgsContrastEnhancement(
            rlayer.dataProvider().dataType(r_band + 1))
        r_ce.setMinimumValue(settings.symbol[i_series]['min'][r_band])
        r_ce.setMaximumValue(settings.symbol[i_series]['max'][r_band])
        r_ce.setContrastEnhancementAlgorithm(
            settings.symbol[i_series]['contrast'])

        g_ce = qgis.core.QgsContrastEnhancement(
            rlayer.dataProvider().dataType(g_band + 1))
        g_ce.setMinimumValue(settings.symbol[i_series]['min'][g_band])
        g_ce.setMaximumValue(settings.symbol[i_series]['max'][g_band])
        g_ce.setContrastEnhancementAlgorithm(
            settings.symbol[i_series]['contrast'])

        b_ce = qgis.core.QgsContrastEnhancement(
            rlayer.dataProvider().dataType(b_band + 1))
        b_ce.setMinimumValue(settings.symbol[i_series]['min'][b_band])
        b_ce.setMaximumValue(settings.symbol[i_series]['max'][b_band])
        b_ce.setContrastEnhancementAlgorithm(
            settings.symbol[i_series]['contrast'])

        # Setup renderer
        renderer = qgis.core.QgsMultiBandColorRenderer(
            rlayer.dataProvider(),
            r_band + 1, g_band + 1, b_band + 1)
        renderer.setRedContrastEnhancement(r_ce)
        renderer.setGreenContrastEnhancement(g_ce)
        renderer.setBlueContrastEnhancement(b_ce)

        # Apply, refresh, and update symbology if needed
        rlayer.setRenderer(renderer)
        if hasattr(rlayer, 'setCacheImage'):
            rlayer.setCacheImage(None)
        rlayer.triggerRepaint()
        qgis.utils.iface.legendInterface().refreshLayerSymbology(rlayer)


def add_clicked_geometry(wkt):
    """ Add geometry as polygon within QGIS

    TODO

    See:
        http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/geometry.html#geometry-construction

    """
    pass