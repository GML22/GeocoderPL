""" Module that collects variety utility functions for geospatial programming """

import functools
import glob
import os
import time
import logging
from functools import lru_cache

import fiona
from osgeo import gdal, osr, ogr
from pyproj import Proj, transform
from shapely.geometry import shape, mapping
from shapely.ops import cascaded_union


def create_logger(name):
    """ Function that creates logging file """

    # Deklaracja najwazniejszych sciezek
    parent_path = os.path.abspath(os.path.join(os.path.join(os.getcwd(), os.pardir), os.pardir))

    # Tworzymy plik loggera
    logging.basicConfig(filename=os.path.join(parent_path, "files\\base_logs.log"), level=logging.DEBUG,
                        format='%(asctime)s %(name)s[%(process)d] %(levelname)s: %(message)s',
                        datefmt='%H:%M:%S', filemode="a")

    # Podstawowe funkcje
    handler = logging.StreamHandler()
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger


def time_decorator(func):
    """ Decorator that logs information about time of function execution """

    @functools.wraps(func)
    def time_wrapper(*args, **kwargs):
        start_time = time.time()
        logger = logging.getLogger('root')
        logger.info("0. Rozpoczęcie wykonywania funkcji '" + func.__name__ + "'")

        # Wykonujemy główną fukcję
        ret_vals = func(*args, **kwargs)

        time_passed = time.time() - start_time
        logger.info("1. Łączny czas wykonywania funkcji '" + func.__name__ + "': {:.2f} sekundy".format(time_passed))

        return ret_vals

    return time_wrapper


@time_decorator
def compress_imgs(img_form, comp_alg, comp_pred):
    """ Function that compress images of given format (e.g. Gtiff) using given compression algorithm (e.g. LZW)
     and predictor of compression (e.g. 2)"""

    translateoptions = gdal.TranslateOptions(gdal.ParseCommandLine("-of " + img_form + " -co COMPRESS= " + comp_alg +
                                                                   " -co PREDICTOR=" + comp_pred + " -co TILED=YES"))
    curr_tif = "org_img.tif"
    gdal.Translate("comp_img.tif", curr_tif, options=translateoptions)


def create_coords_transform(in_epsg, out_epsg, change_map_strateg=False):
    """ Function that creates object that transforms geographical coordinates """

    # Zmieniamy system koordynatow dla gmin
    in_sp_ref = osr.SpatialReference()
    in_sp_ref.ImportFromEPSG(in_epsg)

    # Zmieniamy mapping strategy, bo koordynaty dla gmin podawane sa w odwrotnej kolejnosc tzw. "starej"
    if change_map_strateg:
        in_sp_ref.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    out_sp_ref = osr.SpatialReference()
    out_sp_ref.ImportFromEPSG(out_epsg)

    # Zmieniamy mapping strategy, bo k0ordynaty dla gmin podawane sa w odwrotnej kolejnosc tzw. "starej"
    if change_map_strateg:
        out_sp_ref.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    return osr.CoordinateTransformation(in_sp_ref, out_sp_ref)


def clear_xml_node(curr_node):
    """ Function that clears unnecessary XML nodes from RAM memory """
    curr_node.clear()

    for ancestor in curr_node.xpath('ancestor-or-self::*'):
        while ancestor.getprevious() is not None:
            del ancestor.getparent()[0]


@lru_cache
def get_sectors_params(sekts_num):
    """ Calculating basic parameters of sectors """
    # Ustalamy podstawowe parametry
    plnd_max_szer = 55
    plnd_min_szer = 48
    sekt_szer = (plnd_max_szer - plnd_min_szer) / sekts_num
    plnd_min_dl = 13
    plnd_max_dl = 25
    sekt_dl = (plnd_max_dl - plnd_min_dl) / sekts_num

    return sekt_szer, sekt_dl, plnd_min_szer, plnd_min_dl


def get_sector_codes(poly_centr_y, poly_centr_x, sekts_num):
    """ Function that returns sector code for given coordinates """

    # Wyliczamy finalny kod sektora
    sekt_szer, sekt_dl, plnd_min_szer, plnd_min_dl = get_sectors_params(sekts_num)
    c_sekt_szer = ((poly_centr_y - plnd_min_szer) / sekt_szer).astype(int)
    c_sekt_dl = ((poly_centr_x - plnd_min_dl) / sekt_dl).astype(int)
    return c_sekt_szer, c_sekt_dl


def convert_coords(all_coords, in_system, out_system):
    """ Function that converts multiple coordinates between given systems """

    in_proj = Proj('epsg:' + in_system)
    out_proj = Proj('epsg:' + out_system)
    return transform(in_proj, out_proj, all_coords[:, 0], all_coords[:, 1])
