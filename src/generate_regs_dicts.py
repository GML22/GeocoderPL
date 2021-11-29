""" Module that creates dictionary containing the shapes of regions """

import os
import zipfile

import numpy as np
from matplotlib import path
from osgeo import ogr, osr
from unidecode import unidecode

from geo_utilities import time_decorator


@time_decorator
def create_regs_dicts(fls_path, lyrs_path):
    """ Funtion that creates dictionary containing regions shapes """

    if not os.path.exists(fls_path + "regs_dict.npy"):
        regions_path = lyrs_path + "Granice_adminitracyjne\\00_jednostki_administracyjne.zip"
        assrt_msg = "W folderze '" + lyrs_path + "\\Granice_adminitracyjne' brakuje pliku " + \
                    "'00_jednostki_administracyjne.zip'. Uzupełnij ten plik i uruchom program ponownie!"
        assert os.path.exists(regions_path), assrt_msg

        regions_shapes = get_region_shapes(regions_path)
        all_regs_names = list(regions_shapes.keys())
        t_dict = {"CODE_KEY": {}, "NAME_KEY": {}}
        r_dict = {}

        # Transformujemy wspolrzednie do ukladu 4326 (przy przy okazji korygujemy kolejność współrzędnych)
        shapes = regions_shapes[all_regs_names[0]].GetLayer(0)
        curr_epsg = int(shapes.GetSpatialRef().GetAttrValue("AUTHORITY", 1))
        in_sp_ref = osr.SpatialReference()
        in_sp_ref.ImportFromEPSG(curr_epsg)
        out_sp_ref = osr.SpatialReference()
        out_sp_ref.ImportFromEPSG(4326)
        coord_trans = osr.CoordinateTransformation(in_sp_ref, out_sp_ref)

        # KRAJ
        get_reg_dict('_pan', all_regs_names, regions_shapes, t_dict, coord_trans, r_dict)

        # WOJEWÓDZTWA
        get_reg_dict('_woj', all_regs_names, regions_shapes, t_dict, coord_trans, r_dict)

        # POWIATY
        get_reg_dict('_pow', all_regs_names, regions_shapes, t_dict, coord_trans, r_dict)

        # GMINY
        get_reg_dict('_gmin', all_regs_names, regions_shapes, t_dict, coord_trans, r_dict)

        # Zapisujemy r_dict do pliku
        regs_dict = {"REGIONS": r_dict, "TERYT": t_dict}
        np.save(fls_path + "regs_dict.npy", regs_dict)

    regs_dict = np.load(fls_path + "regs_dict.npy", allow_pickle=True).item()
    return regs_dict


@time_decorator
def get_region_shapes(regions_path):
    """ Function that creates shapes for each regions """

    with zipfile.ZipFile(regions_path, "r") as zfile:
        regions_shapes = {os.path.basename(os.path.normpath(name)): ogr.Open(r'/vsizip/' + regions_path + '/' + name)
                          for name in zfile.namelist() if name[-4:] == ".shp" and ("_gmin" in name or "_pow" in name or
                                                                                   "_woj" in name or "_pan" in name)}
    return regions_shapes


def get_reg_dict(reg_sub, all_regs_names, regions_shapes, t_dict, coord_trans, r_dict):
    """ Function that returns dictionairies with shapes paths """

    kraj_ind = [i for i, s in enumerate(all_regs_names) if reg_sub in s][0]
    file = regions_shapes[all_regs_names[kraj_ind]]
    shapes = file.GetLayer(0)

    for feature in shapes:
        feat_itms = feature.items()
        name = unidecode(feat_itms['JPT_NAZWA_'].upper()).replace("POWIAT ", "")
        teryt = feat_itms['JPT_KOD_JE']
        t_dict["CODE_KEY"][teryt] = name
        geom = feature.geometry()
        geom.Transform(coord_trans)
        pth_l = []

        if geom.GetGeometryName() == "POLYGON":
            geom_ref = geom.GetGeometryRef(0)
            pth_l += [path.Path(np.asarray(geom_ref.GetPoints()), readonly=True, closed=True)]
        else:
            geom_count = geom.GetGeometryCount()
            pth_l += [path.Path(np.asarray(geom.GetGeometryRef(i).GetGeometryRef(0).GetPoints()),
                                readonly=True, closed=True) for i in range(geom_count)]

        if reg_sub == "_pan":
            r_dict["Polska"] = {"Paths": pth_l, "Województwa": {}}
        elif reg_sub == "_woj":
            if teryt not in r_dict["Polska"]["Województwa"]:
                r_dict["Polska"]["Województwa"][teryt] = {"Name": name, "Paths": pth_l, "Powiaty": {}}
            else:
                r_dict["Polska"]["Województwa"][teryt]["Paths"] += pth_l

            if name not in t_dict["NAME_KEY"]:
                t_dict["NAME_KEY"][name] = {"TERYT": [teryt], "POWIATY": {}}
            else:
                t_dict["NAME_KEY"][name]["TERYT"] += [teryt]

        elif reg_sub == "_pow":
            w_name = teryt[:2]

            if teryt not in r_dict["Polska"]["Województwa"][w_name]["Powiaty"]:
                r_dict["Polska"]["Województwa"][w_name]["Powiaty"].update({teryt: {"Name": name, "Paths": pth_l,
                                                                                   "Gminy": {}}})
            else:
                r_dict["Polska"]["Województwa"][w_name]["Powiaty"][teryt]["Paths"] += pth_l

            if name not in t_dict["NAME_KEY"][t_dict["CODE_KEY"][w_name]]["POWIATY"]:
                t_dict["NAME_KEY"][t_dict["CODE_KEY"][w_name]]["POWIATY"][name] = {"TERYT": [teryt], "GMINY": {}}
            else:
                t_dict["NAME_KEY"][t_dict["CODE_KEY"][w_name]]["POWIATY"][name]["TERYT"] += [teryt]
        else:
            w_name = teryt[:2]
            p_name = teryt[:4]

            if teryt not in r_dict["Polska"]["Województwa"][w_name]["Powiaty"][p_name]["Gminy"]:
                r_dict["Polska"]["Województwa"][w_name]["Powiaty"][p_name]["Gminy"].update({
                    teryt: {"Name": name, "Paths": pth_l}})
            else:
                r_dict["Polska"]["Województwa"][w_name]["Powiaty"][p_name]["Gminy"][teryt]["Paths"] += pth_l

            if name in t_dict["NAME_KEY"][t_dict["CODE_KEY"][w_name]]["POWIATY"][t_dict["CODE_KEY"][p_name]]["GMINY"]:
                t_dict["NAME_KEY"][t_dict["CODE_KEY"][w_name]]["POWIATY"][
                    t_dict["CODE_KEY"][p_name]]["GMINY"][name]["TERYT"] += [teryt]
            else:
                t_dict["NAME_KEY"][t_dict["CODE_KEY"][w_name]]["POWIATY"][
                    t_dict["CODE_KEY"][p_name]]["GMINY"][name] = {"TERYT": [teryt]}
