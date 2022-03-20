""" Module that creates dictionary containing the shapes of regions """

import os
import pickle
import zipfile
from collections import OrderedDict

import numpy as np
from matplotlib import path
from osgeo import ogr, osr
from unidecode import unidecode

from geo_utilities import time_decorator


@time_decorator
def create_regs_dicts() -> dict:
    """ Function that creates dictionary containing regions shapes """

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
        fill_regs_dict(regs_shps, crds_trans)

    try:
        # Wczytyujemy z dysku zapisany słownik
        with open(regs_path, 'rb') as file:
            regs_dict = pickle.load(file)
    except FileNotFoundError:
        raise Exception("Pod podanym adresem: '" + regs_path + "' nie ma pliku regs_dict.obj'. Uzupełnij ten plik i " +
                        "uruchom program ponownie!")
    return regs_dict


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
                        "Uzupełnij ten plik i uruchom program ponownie!")
    return regs_shps


def fill_regs_dict(regs_shps: dict, crds_trans: osr.CoordinateTransformation) -> None:
    """ Function that returns dictionairies with shapes paths """

    # Tworzymy słownik regionow i ich ksztaltow
    regs_dict = {}

    # Dla każdego podfolderu w pliku granice administracyjne spisujemy
    for reg_name, reg_file in regs_shps.items():
        shapes = reg_file.GetLayer(0)

        for feature in shapes:
            feat_itms = feature.items()
            name = unidecode(feat_itms['JPT_NAZWA_'].upper()).replace("POWIAT ", "")
            teryt = feat_itms['JPT_KOD_JE']
            geom = feature.geometry()
            geom.Transform(crds_trans)
            path_l = []

            if geom.GetGeometryName() == "POLYGON":
                geom_ref = geom.GetGeometryRef(0)
                path_l += [path.Path(np.asarray(geom_ref.GetPoints()), readonly=True, closed=True)]
            else:
                geom_count = geom.GetGeometryCount()
                path_l += [path.Path(np.asarray(geom.GetGeometryRef(i).GetGeometryRef(0).GetPoints()),
                                     readonly=True, closed=True) for i in range(geom_count)]

            # Ustalamy finalną nazwę regionu
            fin_name = name if len(teryt) < 3 else regs_dict[teryt[:2]][0] + ";" + name if len(teryt) < 5 else \
                regs_dict[teryt[:4]][0] + ";" + name

            # Uzupełniamy słownik numerami TERYT
            if fin_name not in regs_dict:
                regs_dict[fin_name] = [teryt]
            else:
                regs_dict[fin_name] += [teryt]

            # Uzupełniamy słownik obrysami regionów
            if teryt not in regs_dict:
                regs_dict[teryt] = [fin_name, path_l]
            else:
                regs_dict[teryt][1] += path_l

    # Zapisujemy regs_dict na dysku
    with open(os.path.join(os.environ["PARENT_PATH"], os.environ['REGS_PATH']), 'wb') as f:
        pickle.dump(regs_dict, f, pickle.HIGHEST_PROTOCOL)
