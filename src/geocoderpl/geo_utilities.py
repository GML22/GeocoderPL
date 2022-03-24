""" Module that collects variety utility functions for geospatial programming """

import functools
import logging
import os
import re
import time
from functools import lru_cache

import lxml
import numpy as np
import pyproj
from osgeo import osr
from pyproj import Proj, transform


def create_logger(name: str) -> logging.Logger:
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
        logger.info("1. Łączny czas wykonywania funkcji '" + func.__name__ + "' - {:.2f} sekundy".format(time_passed))

        return ret_vals

    return time_wrapper


def create_coords_transform(in_epsg: int, out_epsg: int, change_map_strateg: bool = False) -> \
        osr.CoordinateTransformation:
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


def clear_xml_node(curr_node: lxml.etree.Element) -> None:
    """ Function that clears unnecessary XML nodes from RAM memory """
    curr_node.clear()

    for ancestor in curr_node.xpath('ancestor-or-self::*'):
        while ancestor.getprevious() is not None:
            del ancestor.getparent()[0]


@lru_cache
def get_sectors_params() -> tuple:
    """ Calculating basic parameters of sectors """

    # Ustalamy podstawowe parametry
    sekts_num = int(os.environ["SEKT_NUM"])
    plnd_max_szer = int(os.environ["PLND_MAX_SZER"])
    plnd_min_szer = int(os.environ["PLND_MIN_SZER"])
    sekt_szer = (plnd_max_szer - plnd_min_szer) / sekts_num
    plnd_min_dl = int(os.environ["PLND_MIN_DL"])
    plnd_max_dl = int(os.environ["PLND_MAX_DL"])
    sekt_dl = (plnd_max_dl - plnd_min_dl) / sekts_num
    fin_tup = (sekt_szer, sekt_dl, plnd_min_szer, plnd_min_dl)
    return fin_tup


def get_sector_codes(poly_centr_y: float, poly_centr_x: float) -> (int, int):
    """ Function that returns sector code for given coordinates """

    # Wyliczamy finalny kod sektora
    sek_tup = get_sectors_params()
    sekt_szer = sek_tup[0]
    sekt_dl = sek_tup[1]
    plnd_min_szer = sek_tup[2]
    plnd_min_dl = sek_tup[3]
    c_sekt_szer = ((poly_centr_y - plnd_min_szer) / sekt_szer).astype(int)
    c_sekt_dl = ((poly_centr_x - plnd_min_dl) / sekt_dl).astype(int)
    return c_sekt_szer, c_sekt_dl


def convert_coords(all_coords: np.ndarray, in_system: str, out_system: str) -> pyproj.Transformer:
    """ Function that converts multiple coordinates between given systems """

    in_proj = Proj('epsg:' + in_system)
    out_proj = Proj('epsg:' + out_system)
    return transform(in_proj, out_proj, all_coords[:, 0], all_coords[:, 1])


def reduce_coordinates_precision(geojson_poly: str, precision: int) -> str:
    """ Function that reduce decimal precision of coordinates in GeoJSON file
        0 decimal places is a precision of about 111 km
        1 decimal place is a precsion of about 11 km
        2 decimal places is a precison of about 1.1 km
        3 decimal places is a precison of about 111 m
        4 decimal places is a precison of about 11 m
        5 decimal places is a precison of about 1.1 m
        6 decimal places is a precison of about 11 cm
        7 decimal places is a precison of about 1.1 cm """

    # Tworzymy pattern wyszukujacy liczby w ciagu znakow
    num_patt = r'[-+]?\d*\.\d+|\d+'

    # Wypisujemy wszystkie liczby z danego ciagu znaków i zmniejszamy im precyzje
    all_nums = np.around(np.asarray(re.findall(num_patt, geojson_poly)).astype(float), decimals=precision)
    all_nums_len = len(all_nums)

    # Wypisujemy indesy wszystkich liczb (numery początku i końca liczby)
    num_ids = np.array([(m.start(0), m.end(0)) for m in re.finditer(num_patt, geojson_poly)])

    # Tworzymy macierz, która przechowuje indeksy poczatkowe i koncówe tekstów nie bedacych liczbami
    text_ids = np.zeros((len(num_ids) + 1, 2), dtype=int)
    text_ids[1:, 0] = num_ids[:, 1]
    text_ids[:-1, 1] = num_ids[:, 0]
    text_ids[-1, -1] = len(geojson_poly)

    # Laczymy teksty nie bedace liczbami z liczbami ze zredukowana precyzja w jeden laczny ciag znakow
    fin_geojson = "".join([geojson_poly[row[0]:row[1]] + str(all_nums[i]) if i < all_nums_len else
                           geojson_poly[row[0]:row[1]] for i, row in enumerate(text_ids)])
    return fin_geojson
