""" Module that collects variety utility functions for geospatial programming """

import functools
import logging
import os
import re
import sys
import time
import zipfile
from collections import OrderedDict
from functools import lru_cache
from typing import overload

import geocoder
import numpy as np
import pandas as pd
import pyproj
import sqlalchemy as sa
from lxml import etree
from matplotlib import path
from osgeo import ogr
from osgeo import osr
from pyproj import Proj, transform
from unidecode import unidecode

from db_classes import SQL_ENGINE, BDOT10K, UniqPhrs, AddrArr, TerytCodes, RegJSON
from super_permutations import SuperPerms


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


@time_decorator
def fill_regs_tables() -> None:
    """ Function that fills tables with parameters of regions shapes """

    # Sciezka na dysku z zapisanym slownikiem regionow
    regs_path = os.path.join(os.environ["PARENT_PATH"], os.environ['REGS_PATH'])

    if not os.path.exists(regs_path):
        # Podstawowe parametry
        regs_shps = get_region_shapes()

        # Transformujemy wspolrzednie do ukladu 4326 (przy okazji korygujemy kolejność współrzędnych)
        f_shp = next(iter(regs_shps.values())).GetLayer(0)
        curr_epsg = int(f_shp.GetSpatialRef().GetAttrValue("AUTHORITY", 1))
        in_sp_ref = osr.SpatialReference()
        in_sp_ref.ImportFromEPSG(curr_epsg)
        out_sp_ref = osr.SpatialReference()
        out_sp_ref.ImportFromEPSG(int(os.environ['WORLD_CRDS']))
        crds_trans = osr.CoordinateTransformation(in_sp_ref, out_sp_ref)

        # Wypelniamy słownik ze sciezkami regionow
        f_regs_tables(regs_shps, crds_trans)


@time_decorator
def get_region_shapes() -> OrderedDict:
    """ Function that creates shapes for each regions """

    # Scieżka do pliku z jednostkami administracyjnymi
    ja_path = os.path.join(os.environ["PARENT_PATH"], os.environ['JA_PATH'])

    try:
        with zipfile.ZipFile(ja_path, "r") as zfile:
            regs_shps = OrderedDict(
                sorted({os.path.basename(os.path.normpath(name)): ogr.Open(r'/vsizip/' + ja_path + '/' + name)
                        for name in zfile.namelist() if name[-4:] == ".shp" and
                        ("_gmin" in name or "_pow" in name or "_woj" in name or "_pan" in name)}.items()))
    except FileNotFoundError:
        raise Exception("Pod podanym adresem: '" + ja_path + "' nie ma pliku '00_jednostki_administracyjne.zip'. " +
                        "Pobierz ten plik ze stronyu: 'https://dane.gov.pl/pl/dataset/726,panstwowy-rejestr-granic-i-" +
                        "powierzchni-jednostek-podziaow-terytorialnych-kraju/resource/29515' i uruchom program " +
                        "ponownie!")
    return regs_shps


def f_regs_tables(regs_shps: dict, crds_trans: osr.CoordinateTransformation) -> None:
    """ Function that returns dictionairies with shapes paths """

    # Tworzymy słownik regionow i ich ksztaltow
    name_list = []
    teryt_list = []

    # Dla każdego podfolderu w pliku granice administracyjne spisujemy
    for reg_name, reg_file in regs_shps.items():
        shapes = reg_file.GetLayer(0)

        # Ustalamy finalną nazwę regionu
        with sa.orm.Session(SQL_ENGINE) as session:
            for feature in shapes:
                feat_itms = feature.items()
                name = unidecode(feat_itms['JPT_NAZWA_'].upper()).replace("POWIAT ", "")
                teryt = feat_itms['JPT_KOD_JE']
                geom = feature.geometry()
                geom.Transform(crds_trans)

                if geom.GetGeometryName() == "POLYGON":
                    geom_ref = geom.GetGeometryRef(0)
                    geom_json = geom_ref.ExportToJson()
                else:
                    geom_cnt = geom.GetGeometryCount()
                    geom_json = ";".join([geom.GetGeometryRef(i).GetGeometryRef(0).ExportToJson()
                                          for i in range(geom_cnt)])

                # Ustalamy finalna nazwe regionu TERYT
                if len(teryt) < 3:
                    fin_name = name
                elif len(teryt) < 5:
                    json_name = session.query(RegJSON.json_name).filter(RegJSON.json_teryt == teryt[:2]).all()[0][0]
                    fin_name = json_name + ";" + name
                else:
                    json_name = session.query(RegJSON.json_name).filter(RegJSON.json_teryt == teryt[:4]).all()[0][0]
                    fin_name = json_name + ";" + name

                # Uzupełniamy tabele TERYT_TABLE
                if fin_name not in name_list:
                    name_list.append(fin_name)
                    session.add(TerytCodes(fin_name, teryt))
                else:
                    c_teryt = session.query(TerytCodes.teryt_code).filter(TerytCodes.teryt_name == fin_name).all()[0][0]
                    n_teryt = c_teryt + ";" + teryt
                    session.query(TerytCodes).filter(TerytCodes.teryt_name == fin_name).update({'teryt_code': n_teryt})

                # Uzupełniamy tabele JSON_TABLE
                if teryt not in teryt_list:
                    teryt_list.append(teryt)
                    session.add(RegJSON(fin_name, teryt, geom_json))
                else:
                    c_json = session.query(RegJSON.json_shape).filter(RegJSON.json_teryt == teryt).all()[0][0]
                    n_json = c_json + ";" + geom_json
                    session.query(RegJSON).filter(RegJSON.json_teryt == teryt).update({'json_shape': n_json})

            session.commit()


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


def clear_xml_node(curr_node: etree.Element) -> None:
    """ Function that clears unnecessary XML nodes from RAM memory """
    curr_node.clear()

    for ancestor in curr_node.xpath('ancestor-or-self::*'):
        while ancestor.getprevious() is not None:
            del ancestor.getparent()[0]


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


def get_super_permut_dict(max_len: int) -> dict:
    """ Function that creates indices providing superpermutations for lists of strings with length of maximum 5
    elements """

    return {i: SuperPerms(i).fin_super_perm_ids for i in range(1, max_len + 1)}


def csv_to_dict(c_path: str) -> dict:
    """ Function that imports CSV file and creates dictionairy from first two columns of that file """

    try:
        x_kod = pd.read_csv(c_path, sep=";", dtype=str, engine='c', header=None, low_memory=False).values
    except FileNotFoundError:
        raise Exception("Pod adresem: '" + c_path + "' nie ma pliku potrzebnego pliku. Uzupełnij ten plik i  uruchom " +
                        "program ponownie!")
    return {row[0]: row[1] for row in x_kod}


def points_inside_polygon(grouped_regions: dict, woj_name: str, trans_crds: np.ndarray, points_list: list,
                          popraw_list: list, dists_list: list, zrodlo_list: list, bdot10k_ids: np.ndarray,
                          bdot10k_dist: np.ndarray, sekt_kod_list: list, dod_opis_list: list, addr_phrs_list: list,
                          addr_phrs_len: int) -> None:
    """ Function that checks if given points are inside polygon of their districts and finds closest building shape for
     given PRG point"""

    for i, regions, coords_inds in enumerate(grouped_regions.items()):
        pow_name, gmin_name = regions
        if pow_name != '' and gmin_name != '':
            logging.info(gmin_name)
            pow_name = get_corr_reg_name(unidecode(pow_name.upper()))
            gmin_name = get_corr_reg_name(unidecode(gmin_name.upper()))

            # Pobieramy kody TERYT danej gminy
            with sa.orm.Session(SQL_ENGINE) as session:
                t_code = woj_name + ";" + pow_name + ";" + gmin_name
                gmin_codes = session.query(TerytCodes.teryt_code).filter(TerytCodes.teryt_name == t_code).all()[0][0]

            gmin_codes = gmin_codes.split(";")
            c_paths = []

            # Dla kazdego kodu TERYT gminy pobieramy sciezki wielokatow tej gminy
            for gmn_code in gmin_codes:
                with sa.orm.Session(SQL_ENGINE) as session:
                    c_json = session.query(RegJSON.json_shape).filter(RegJSON.json_teryt == gmn_code).all()[0][0]

                pth = path.Path(np.asarray(ogr.CreateGeometryFromJson(c_json).GetPoints()), readonly=True, closed=True)
                c_paths += pth

            curr_coords = trans_crds[coords_inds, ::-1]
            points_flags = points_in_shape(c_paths, curr_coords)

            # Dla punktow odresowych PRG, ktore znajduja sie poza granicami wielokatow swoich gmin przeprowadzamy
            # ponowne geokodowanie przy pomocy OpenStreetMap
            if not all(points_flags):
                outside_pts = curr_coords[~points_flags]
                outside_inds = coords_inds[~points_flags]

                for j, c_ind in enumerate(outside_inds):
                    c_row = [lst[c_ind] for lst in points_list]
                    c_pow, c_gmin, c_miejsc, c_miejsc2, c_ulica, c_numer = c_row[1:7]
                    address = ""

                    if c_miejsc2 != '' and c_ulica != '':
                        address = c_numer + ", " + c_ulica + ", " + c_miejsc2 + ", " + c_miejsc + ", " + c_gmin + \
                                  ", " + c_pow
                    elif c_miejsc2 == '' and c_ulica != '':
                        address = c_numer + ", " + c_ulica + ", " + c_miejsc + ", " + c_gmin + ", " + c_pow
                    elif c_ulica == '' and c_miejsc2 != '':
                        address = c_numer + ", " + c_miejsc2 + ", " + c_miejsc + ", " + c_gmin + ", " + c_pow
                    elif c_ulica == '' and c_miejsc2 == '':
                        address = c_numer + ", " + c_miejsc + ", " + c_gmin + ", " + c_pow

                    get_osm_coords(address, outside_pts[j, :], c_paths, popraw_list, c_ind, c_row, dists_list,
                                   zrodlo_list)

            # Dla każdego punktu PRG wyszukujemy najbliższy mu wielokat z bazy BDOT10K
            get_bdot10k_id(curr_coords, coords_inds, bdot10k_ids, bdot10k_dist, sekt_kod_list, dod_opis_list,
                           addr_phrs_list, addr_phrs_len)


@lru_cache
def get_corr_reg_name(curr_name: str) -> str:
    """ Function that corrects wrong regions names """
    # Specjalny wyjatek, bo w danych PRG jest powiat "JELENIOGORSKI", a od 2021 roku powiat ten nazywa sie "KARKONOSKI",
    # wiec trzeba to poprawic
    if curr_name == "JELENIOGORSKI":
        return "KARKONOSKI"

    # Kolejny wyjatek, bo w danych PRG jest gmina "SITKOWKA-NOWINY", a od 2021 roku gmina ta nazywa sie "NOWINY", wiec
    # trzeba to poprawic
    elif curr_name == "SITKOWKA-NOWINY":
        return "NOWINY"

    # Kolejny wyjatek, bo w danych PRG jest gmina "SLUPIA (KONECKA)", a od 2018 roku gmina ta nazywa sie
    # "SLUPIA KONECKA", wiec trzeba to poprawic
    elif curr_name == "SLUPIA (KONECKA)":
        return "SLUPIA KONECKA"
    else:
        return curr_name


def points_in_shape(c_paths: list, curr_coords: np.ndarray) -> np.ndarray:
    """ Checking if point lies inside shape of district """

    points_flags = np.zeros(len(curr_coords), dtype=bool)

    for pth in c_paths:
        points_flags = np.logical_or(points_flags, pth.contains_points(curr_coords))

    return points_flags


def get_osm_coords(address: str, outside_pts: np.ndarray, c_paths: list, popraw_list: list, c_ind: int,
                   c_row: list, dists_list: list, zrodlo_list: list) -> None:
    """ Function that returns OSM coordinates of address point or distance from the district shapefile """

    status_code = 500
    geo_addr = None

    while status_code != 200:
        g = geocoder.osm(address)
        geo_addr = g.osm
        status_code = g.status_code
        time.sleep(5)

    if geo_addr is not None:
        # Specjalnie oznaczamy 'x' z adresu jako 'y_val' i 'y' jako "x_val", bo notacja stosowana w geocoderze jest
        # odwrotna od tej w pakiecie GDAL
        x_val = geo_addr["y"]
        y_val = geo_addr["x"]

        if round(x_val, 3) != round(outside_pts[1], 3) or round(y_val, 3) != round(outside_pts[0], 3):
            in_flag = False

            for pth in c_paths:
                if pth.contains_point((y_val, x_val)):
                    in_flag = True
                    break

            if not in_flag:
                popraw_list[c_ind] = 0
                max_dist = calc_pnt_dist(c_paths, c_row[-2], c_row[-1])
                dists_list[c_ind] = max_dist
            else:
                outside_pts[1] = x_val
                outside_pts[0] = y_val
                zrodlo_list[c_ind] = "OSM"
        else:
            popraw_list[c_ind] = 0
            max_dist = calc_pnt_dist(c_paths, c_row[-2], c_row[-1])
            dists_list[c_ind] = max_dist


def calc_pnt_dist(c_paths: list, x_val: float, y_val: float) -> float:
    """ Function that calculates distances of point to given polygon """

    # Zaczynamy od dużej liczby
    min_dist = sys.maxsize

    for pth in c_paths:
        c_point = ogr.Geometry(ogr.wkbPoint)
        c_point.AddPoint(y_val, x_val)
        c_ring = ogr.Geometry(ogr.wkbLinearRing)
        [c_ring.AddPoint(row[0], row[1]) for row in pth.vertices]
        c_poly = ogr.Geometry(ogr.wkbPolygon)
        c_poly.AddGeometry(c_ring)
        c_poly.Transform(create_coords_transform(int(os.environ['WORLD_CRDS']), int(os.environ['PL_CRDS']), True))
        c_dist = c_point.Distance(c_poly)
        min_dist = c_dist if c_dist < min_dist else min_dist

    return min_dist


def get_bdot10k_id(curr_coords: np.ndarray, coords_inds: np.ndarray, bdot10k_ids: np.ndarray, bdot10k_dist: np.ndarray,
                   sekt_kod_list: list, dod_opis_list: list, addr_phrs_list: list, addr_phrs_len: int) -> None:
    """ Function that returns id and distance of polygon closest to PRG point """

    # Ustalamy sektory dla wybranych przez naas punktow PRG
    coords_sekts = np.asarray(get_sector_codes(curr_coords[:, 1], curr_coords[:, 0])).T
    coords_sekts_zfill = np.char.chararray.zfill(coords_sekts.astype(str), 3)
    sekt_kod_list[coords_inds] = np.char.add(np.char.add(coords_sekts_zfill[:, 0], '_'), coords_sekts_zfill[:, 1])

    # Dla każdego wybranego sektora dobieramy sektory, ktore go otaczaja, w ten sposob uzyskujac 9 sektorow dla kazdego
    # punktu PRG, z których wybieramy unikalne kombinacje sektorow
    sekt_num = int(os.environ["SEKT_NUM"])
    unique_sekts, sekts_ids = np.unique([[str(max(i, 0)).zfill(3) + "_" + str(min(j, sekt_num - 1)).zfill(3)
                                          for i in range(szer - 1, szer + 2) for j in range(dlug - 1, dlug + 2)]
                                         for szer, dlug in coords_sekts], axis=0, return_inverse=True)
    sekt_szer, sekt_dl, plnd_min_szer, plnd_min_dl = get_sectors_params()

    # Dla każdej unikalnej kombinacji sektorow przeprowadzamy wyszukiwanie obrysow budynkow
    for x, unq_sekt in enumerate(unique_sekts):
        # Wybieramy koordynaty dla biezacych sektorow
        curr_uniqs = sekts_ids == x
        c_coords = curr_coords[curr_uniqs, :]
        crds_inds = coords_inds[curr_uniqs]
        c_coords = c_coords[:, [1, 0]]
        c_coords_smpl = np.float32(c_coords)
        c_len = len(c_coords)

        # Wybieramy z tablicy BDOT10K_TABLE wszystkie budynki z zadanych sektorow
        with sa.orm.Session(SQL_ENGINE) as session:
            pow_bubd_arr = np.asarray(session.query(BDOT10K.bdot10k_bubd_id, BDOT10K.centr_lat, BDOT10K.centr_long,
                                                    BDOT10K.opis_budynku, BDOT10K.bubd_geojson
                                                    ).filter(BDOT10K.kod_sektora.in_(unq_sekt)).all(), dtype=object)
            pow_centr_smpl = pow_bubd_arr[:, 1:3].astype(np.float32)

        # Wyliczamy odleglosci budynkow od srodka biezacego sektora i wybieramy tylko te budynki, ktore znajduja sie
        # w odleglosci sekt_rad * szerokosc (dlugosc) sektora - w ten sposob mamy pewnosc, ze wlasciwie przypisane beda
        # budynki do punktow adresowych znajdujacych sie na krawedziach sektorow - unikamy sytuacji w ktorej punkt
        # adresowy znajduje sie na krawedzi jednego sektora a centroid budynku na krawedzi sasiedniego sektora
        curr_sekt = unq_sekt[4].split("_")  # biezacy sektor zawsze bedzie 5 na liscie unq_sekt
        sekt_centr_sz = plnd_min_szer + (float(curr_sekt[0]) + 0.5) * sekt_szer
        sekt_centr_dl = plnd_min_dl + (float(curr_sekt[1]) + 0.5) * sekt_dl
        pow_centr_odl = np.abs(pow_centr_smpl - [sekt_centr_sz, sekt_centr_dl])
        s_rad = float(os.environ["SEKT_RAD"])
        pow_fin_mask = np.logical_and(pow_centr_odl[:, 0] <= s_rad * sekt_szer, pow_centr_odl[:, 0] <= s_rad * sekt_dl)
        pow_centr_smpl = pow_centr_smpl[pow_fin_mask, :]
        pow_bubd_arr = pow_bubd_arr[pow_fin_mask, :]
        pow_len = len(pow_bubd_arr)

        # Upraszczamy precyzje liczb do formatu float32, bo przy ukladzie współrzednych EPSG 4326, taka precyzja jest
        # wystarczajaca - liczby zaookraglane sa do 6 miejsc po przecinku co daje precyzje koordynatow na poziomie
        # około 11 cm
        on1 = np.ones((pow_len, 1), dtype=np.float32)
        on2 = np.ones((c_len, 1), dtype=np.float32)

        # Dla uproszczenia wyliczamy odleglosc euklidesowa pomiedzy punktami PRG a centroidami budynkow BUBD
        # Dla obszaru wielkosci powiatu odleglosc euklidesowa niewiele sie będzie różnic od dokladnej odleglosci
        # (na sferze)
        eukl_dists = np.sqrt(((np.kron(c_coords_smpl, on1) -
                               np.kron(on2, pow_centr_smpl)) ** 2).sum(1)).reshape((c_len, pow_len))

        # Wybieramy 10 najblizszych budynkow (w mierze euklidesowej) dla wszystkich punktow PRG
        top10_ids = eukl_dists.argsort()[:, :10]
        top10_geojson = pow_bubd_arr[top10_ids, -1]

        # Dla kazdego z punktow adresowych PRG wybieramy 10 najblizszych mu budynkow (pod katem odleglosci euklidesowej
        # od centroidow tych budynkow) i dla tych 10 budynkow znajdujemy dokladna odleglosc punktu adresowego od
        # wielokatow poszczegolnych budynkow - wybieramy wielokat najbliższy danemu punktowi PRG i zapisujemy jego
        # indeks w bazie w raz z wyliczona odlegloscia
        gen_fin_bubds_ids(c_coords, c_len, top10_geojson, top10_ids, bdot10k_dist, bdot10k_ids, crds_inds, pow_bubd_arr,
                          dod_opis_list, curr_sekt, addr_phrs_list, addr_phrs_len)


@lru_cache
def get_sectors_params() -> tuple:
    """ Calculating basic parameters of sectors """

    # Ustalamy podstawowe parametry
    sekt_num = int(os.environ["SEKT_NUM"])
    plnd_max_szer = int(os.environ["PLND_MAX_SZER"])
    plnd_min_szer = int(os.environ["PLND_MIN_SZER"])
    sekt_szer = (plnd_max_szer - plnd_min_szer) / sekt_num
    plnd_min_dl = int(os.environ["PLND_MIN_DL"])
    plnd_max_dl = int(os.environ["PLND_MAX_DL"])
    sekt_dl = (plnd_max_dl - plnd_min_dl) / sekt_num
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


def gen_fin_bubds_ids(c_coords: np.ndarray, c_len: int, top10_geojson: np.ndarray, top10_ids: np.ndarray,
                      bdot10k_dist: np.ndarray, bdot10k_ids: np.ndarray, crds_inds: np.ndarray,
                      pow_bubd_arr: np.ndarray, dod_opis_list: list, curr_sekt: int, addr_phrs_list: list,
                      addr_phrs_len: int) -> None:
    """ Function that finds closest buidling shape for given PRG point """

    trans_szer, trans_dlug = convert_coords(c_coords, os.environ['WORLD_CRDS'], os.environ['PL_CRDS'])
    coords_pts = [ogr.Geometry(ogr.wkbPoint) for _ in range(c_len)]
    [c_point.AddPoint(trans_dlug[i], trans_szer[i]) for i, c_point in enumerate(coords_pts)]
    c_db_len = addr_phrs_len
    c_adr_phr = ""

    with sa.orm.Session(SQL_ENGINE) as session:
        addr_phrs_uniq = session.query(UniqPhrs.uniq_phrs).all()[0][0]

    for i, c_point in enumerate(coords_pts):
        fin_dist = 10 ** 6
        fin_idx = 0

        for j, geojson in enumerate(top10_geojson[i]):
            c_poly = ogr.CreateGeometryFromJson(geojson)
            c_poly.Transform(create_coords_transform(int(os.environ['WORLD_CRDS']), int(os.environ['PL_CRDS']), True))
            c_dist = c_point.Distance(c_poly)

            if c_dist == 0.0:
                fin_dist = c_dist
                fin_idx = j
                break
            elif c_dist < fin_dist:
                fin_dist = c_dist
                fin_idx = j

        # Przypisujemy do punktow adresowych indeksy najblizszych budunkow oraz odleglosci od nich
        c_inds = crds_inds[i]
        pow_bubd_ids = top10_ids[i, fin_idx]

        # Uzupelniamy liste podstawowych informacji o adresie
        c_pts_sp = addr_phrs_list[c_inds]
        c_adr_phr += " " + " ".join(c_pts_sp)

        # Uzupelniamy liste dodatkowych informacji o adresie
        c_dod_inf = pow_bubd_arr[pow_bubd_ids, 3]

        # Jeżeli najkrotszy znaleziony dystans jest krótszy niż maksymalna zakladana odleglosc punktu adresowego PRG od
        # budynku BDOT10k to przypisujemy dany budynek do punktu adresowego
        if fin_dist < int(os.environ['MAX_DIST']):
            bdot10k_dist[c_inds] = fin_dist
            bdot10k_ids[c_inds] = pow_bubd_arr[pow_bubd_ids, 0]

            if len(c_dod_inf) > 0:
                dod_opis_list[c_inds] = c_dod_inf
                c_dod_str = unidecode(c_dod_inf).upper()
                c_adr_phr += " " + str(c_pts_sp[0]) + " " + c_dod_str + " " + str(c_pts_sp[1])

                for inf in c_dod_str.replace(", ", " ").split(" "):
                    if inf not in addr_phrs_uniq:
                        addr_phrs_uniq += inf + " "

        c_adr_phr += " [" + str(c_db_len + c_inds + 1) + "]\n"

    # Uzupelniamy baze danych ciagami slow adresowych
    with sa.orm.Session(SQL_ENGINE) as session:
        # Zapisujemy do bazy unikalne frazy
        session.query(UniqPhrs).filter(UniqPhrs.uniq_id == 1).update({'uniq_phrs': addr_phrs_uniq})

        # Zapisujemy do bazy ciagi adresow
        c_col = 'COL_' + curr_sekt[1]
        c_row = int(curr_sekt[0])
        c_str = session.query(AddrArr.__table__.c[c_col]).filter(AddrArr.addr_id == c_row).all()[0][0] + c_adr_phr
        session.query(AddrArr).filter(AddrArr.addr_id == c_row).update({c_col: c_str})
        session.commit()


@overload
def convert_coords(all_coords: list, in_system: str, out_system: str) -> pyproj.Transformer:
    ...


@overload
def convert_coords(all_coords: np.ndarray, in_system: str, out_system: str) -> pyproj.Transformer:
    ...


def convert_coords(all_coords, in_system, out_system) -> pyproj.Transformer:
    """ Function that converts multiple coordinates between given systems """

    in_proj = Proj('epsg:' + in_system)
    out_proj = Proj('epsg:' + out_system)

    if isinstance(all_coords, list):
        return transform(in_proj, out_proj, all_coords[0], all_coords[1])
    else:
        return transform(in_proj, out_proj, all_coords[:, 0], all_coords[:, 1])
