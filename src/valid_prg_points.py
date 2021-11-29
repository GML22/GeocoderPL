""" Module for converting spatial reference of PRG points from 2180 to 4326, checking if given PRG point belongs to
shapefile of its district and determining closest building shape for given PRG point """
import geocoder
import numpy as np
import pandas as pd
from unidecode import unidecode

from geo_utilities import *


@time_decorator
def check_prg_points(points_arr, regs_dict, woj_name, cursor, addr_phrs_dict, sekt_num, max_dist):
    """ Function that converts spatial reference of PRG points from 2180 to 4326, checks if given PRG point belongs
    to shapefile of its district and finds closest building shape for given PRG point """

    # Konwertujemy wpółrzędne do oczekiwanego układu wspolrzednych 4326 i dodajemy do bazy danych kolumny zawierajace
    # przekonwertowane wspolrzedne
    trans_szer, trans_dlug = convert_coords(points_arr[:, -2:], "2180", "4326")

    # Grupujemy kolumny z nazwami powiatow oraz gmin i sprawdzamy czy punkty adresowe z bazy PRG znajduja sie wewnatrz
    # shapefili ich gmin
    df_regions = pd.DataFrame(points_arr[:, 1:3])
    df_regions.columns = ['POWIAT', 'GMINA']
    grouped_regions = df_regions.groupby(['POWIAT', 'GMINA'], as_index=False).groups

    # Tworzymy system transformujący wspolrzedne geograficzne
    coord_trans = create_coords_transform(4326, 2180, True)

    # Tworzymy inne przydatne obiekty
    woj_idx = woj_name.rfind("_") + 1
    woj_name = unidecode(woj_name[woj_idx:-4].upper())
    pts_arr_shp = points_arr.shape
    zrodlo_list = ['PRG'] * pts_arr_shp[0]
    popraw_list = [1] * pts_arr_shp[0]
    dists_list = [0.0] * pts_arr_shp[0]
    bdot10k_ids = np.zeros(pts_arr_shp[0], dtype=int)
    bdot10k_dist = np.zeros(pts_arr_shp[0])
    sekt_kod_list = np.full(pts_arr_shp[0], fill_value='', dtype='<U7')
    dod_opis_list = np.full(pts_arr_shp[0], fill_value='', dtype=object)

    # Dla każdej gminy i powiatu sprawdzamy czy punkty do nich przypisane znajduja sie wewnatrz wielokata danej gminy
    # oraz znajdujemy najbliższy budynek do danego punktu PRG
    points_inside_polygon(grouped_regions, regs_dict, woj_name, trans_dlug, trans_szer, points_arr, popraw_list,
                          coord_trans, dists_list, zrodlo_list, bdot10k_ids, bdot10k_dist, sekt_kod_list, dod_opis_list,
                          cursor, addr_phrs_dict, sekt_num, max_dist)

    # Tworzymy finalna macierz informacji, ktora zapiszemy w bazie
    fin_points_arr = np.empty((pts_arr_shp[0], pts_arr_shp[1] + 7), dtype=object)
    fin_points_arr[:, :(pts_arr_shp[1] - 2)] = points_arr[:, :-2]
    fin_points_arr[:, (pts_arr_shp[1] - 2)] = trans_szer
    fin_points_arr[:, (pts_arr_shp[1] - 1)] = trans_dlug
    fin_points_arr[:, pts_arr_shp[1]] = zrodlo_list
    fin_points_arr[:, pts_arr_shp[1] + 1] = popraw_list
    fin_points_arr[:, pts_arr_shp[1] + 2] = dists_list
    fin_points_arr[:, pts_arr_shp[1] + 3] = bdot10k_ids
    fin_points_arr[:, pts_arr_shp[1] + 4] = bdot10k_dist
    fin_points_arr[:, pts_arr_shp[1] + 5] = sekt_kod_list
    fin_points_arr[:, pts_arr_shp[1] + 6] = dod_opis_list
    return fin_points_arr


def points_in_shape(c_paths, curr_coords):
    """ Checking if point lies inside shape of district """

    points_flags = np.zeros(len(curr_coords), dtype=bool)

    for path in c_paths:
        points_flags = np.logical_or(points_flags, path.contains_points(curr_coords))

    return points_flags


def points_inside_polygon(grouped_regions, regs_dict, woj_name, trans_dlug, trans_szer, points_arr, popraw_list,
                          coord_trans, dists_lists, zrodlo_list, bdot10k_ids, bdot10k_dist, sekt_kod_list,
                          dod_opis_list, cursor, addr_phrs_dict, sekt_num, max_dist):
    """ Function that checks if given points are inside polygon of their districts and finds closest building shape for
     given PRG point"""

    for regions, coords_inds in grouped_regions.items():
        pow_name, gmin_name = regions
        if pow_name != '' and gmin_name != '':
            print(gmin_name + ": " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
            pow_name = get_corr_reg_name(unidecode(pow_name.upper()))
            gmin_name = get_corr_reg_name(unidecode(gmin_name.upper()))
            t_dict = regs_dict["TERYT"]
            r_dict = regs_dict["REGIONS"]

            # Pobieramy kody TERYT danej gminy
            gmin_codes = t_dict["NAME_KEY"][woj_name]["POWIATY"][pow_name]["GMINY"][gmin_name]["TERYT"]
            woj_code = gmin_codes[0][:2]
            pow_code = gmin_codes[0][:4]
            c_paths = []

            # Dla kazdego kodu TERYT gminy pobieramy sciezki wielokatow tej gminy
            for gmn_code in gmin_codes:
                c_paths += r_dict["Polska"]["Województwa"][woj_code]["Powiaty"][pow_code]["Gminy"][gmn_code]["Paths"]

            curr_coords = np.column_stack((trans_dlug[coords_inds], trans_szer[coords_inds]))
            points_flags = points_in_shape(c_paths, curr_coords)

            # Dla punktow odresowych PRG, ktore znajduja sie poza granicami wielokatow swoich gmin przeprowadzamy
            # ponowne geokodowanie przy pomocy OpenStreetMap
            if not all(points_flags):
                outside_pts = curr_coords[~points_flags]
                outside_inds = coords_inds[~points_flags]

                for i, c_ind in enumerate(outside_inds):
                    c_row = points_arr[c_ind]
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

                    get_osm_coords(address, outside_pts[i, :], c_paths, popraw_list, c_ind, c_row, coord_trans,
                                   dists_lists, zrodlo_list)

            # Dla każdego punktu PRG wyszukujemy najbliższy mu wielokat z bazy BDOT10K
            get_bdot10k_id(curr_coords, coords_inds, bdot10k_ids, bdot10k_dist, sekt_kod_list, dod_opis_list, cursor,
                           coord_trans, addr_phrs_dict, sekt_num, max_dist)


def get_osm_coords(address, outside_pts, c_paths, popraw_list, c_ind, c_row, coord_trans, dists_lists, zrodlo_list):
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

            for path in c_paths:
                if path.contains_point((y_val, x_val)):
                    in_flag = True
                    break

            if not in_flag:
                popraw_list[c_ind] = 0
                max_dist = calc_pnt_dist(c_paths, c_row[-2], c_row[-1], coord_trans)
                dists_lists[c_ind] = max_dist
            else:
                outside_pts[1] = x_val
                outside_pts[0] = y_val
                zrodlo_list[c_ind] = "OSM"
        else:
            popraw_list[c_ind] = 0
            max_dist = calc_pnt_dist(c_paths, c_row[-2], c_row[-1], coord_trans)
            dists_lists[c_ind] = max_dist


def calc_pnt_dist(c_paths, x_val, y_val, coord_trans):
    """ Function that calculates distances of point to given polygon """
    min_dist = 1000000.0

    for path in c_paths:
        c_point = ogr.Geometry(ogr.wkbPoint)
        c_point.AddPoint(float(y_val), float(x_val))
        c_ring = ogr.Geometry(ogr.wkbLinearRing)
        [c_ring.AddPoint(row[0], row[1]) for row in path.vertices]
        c_poly = ogr.Geometry(ogr.wkbPolygon)
        c_poly.AddGeometry(c_ring)
        c_poly.Transform(coord_trans)
        c_dist = c_point.Distance(c_poly)
        min_dist = c_dist if c_dist < min_dist else min_dist

    return min_dist


def get_bdot10k_id(curr_coords, coords_inds, bdot10k_ids, bdot10k_dist, sekt_kod_list, dod_opis_list, cursor,
                   coord_trans, addr_phrs_dict, sekt_num, max_dist):
    """ Function that returns id and distance of polygon closest to PRG point """

    # Ustalamy sektory dla wybranych przez naas punktow PRG
    coords_sekts = np.asarray(get_sector_codes(curr_coords[:, 1], curr_coords[:, 0], sekt_num)).T
    coords_sekts_zfill = np.char.chararray.zfill(coords_sekts.astype(str), 3)
    sekt_kod_list[coords_inds] = np.char.add(np.char.add(coords_sekts_zfill[:, 0], '_'), coords_sekts_zfill[:, 1])

    # Dla każdego wybranego sektora dobieramy sektory, ktore go otaczaja, w ten sposob uzyskujac 9 sektorow dla kazdego
    # punktu PRG, z których wybieramy unikalne kombinacje sektorow
    unique_sekts, sekts_ids = np.unique([[str(max(i, 0)).zfill(3) + "_" + str(min(j, sekt_num - 1)).zfill(3)
                                          for i in range(szer - 1, szer + 2) for j in range(dlug - 1, dlug + 2)]
                                         for szer, dlug in coords_sekts], axis=0, return_inverse=True)
    sekt_szer, sekt_dl, plnd_min_szer, plnd_min_dl = get_sectors_params(sekt_num)

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
        query_end = "('" + "', '".join(unq_sekt) + "')"
        cursor.execute("SELECT BDOT10K_BUBD_ID, CENTROID_LAT, CENTROID_LONG, OPIS_BUDYNKU, BUBD_GEOJSON FROM " +
                       "BDOT10K_TABLE WHERE KOD_SEKTORA IN " + query_end)
        pow_bubd_arr = np.asarray(cursor.fetchall(), dtype=object)
        pow_centr_smpl = pow_bubd_arr[:, 1:3].astype(np.float32)

        # Wyliczamy odleglosci budynkow od srodka biezacego sektora i wybieramy tylko te budynki, ktore znajduja sie
        # w odleglosci 0,52 * szerokosc (dlugosc) sektora - w ten sposob mamy pewnosc, ze wlasciwie przypisane beda
        # budynki do punktow adresowych znajdujacych sie na krawedziach sektorow - unikamy sytuacji w ktorej punkt
        # adresowy znajduje sie na krawedzi jednego sektora a centroid budynku na krawedzi sasiedniego sektora
        curr_sekt = unq_sekt[4].split("_")  # biezacy sektor zawsze bedzie 5 na liscie unq_sekt
        sekt_centr_sz = plnd_min_szer + (float(curr_sekt[0]) + 0.5) * sekt_szer
        sekt_centr_dl = plnd_min_dl + (float(curr_sekt[1]) + 0.5) * sekt_dl
        pow_centr_odl = np.abs(pow_centr_smpl - [sekt_centr_sz, sekt_centr_dl])
        pow_fin_mask = np.logical_and(pow_centr_odl[:, 0] <= 0.52 * sekt_szer, pow_centr_odl[:, 0] <= 0.52 * sekt_dl)
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
        c_addr_arr = addr_phrs_dict["ADDR_ARR"][int(curr_sekt[0]), int(curr_sekt[1])]
        gen_fin_bubds_ids(c_coords, c_len, top10_geojson, top10_ids, coord_trans, bdot10k_dist, bdot10k_ids,
                          crds_inds, pow_bubd_arr, c_addr_arr, dod_opis_list, addr_phrs_dict, max_dist)


def gen_fin_bubds_ids(c_coords, c_len, top10_geojson, top10_ids, coord_trans, bdot10k_dist, bdot10k_ids, crds_inds,
                      pow_bubd_arr, c_addr_arr, dod_opis_list, addr_phrs_dict, max_dist):
    """ Function that finds closest buidling shape for given PRG point """

    trans_szer, trans_dlug = convert_coords(c_coords, "4326", "2180")
    coords_pts = [ogr.Geometry(ogr.wkbPoint) for _ in range(c_len)]
    [c_point.AddPoint(trans_dlug[i], trans_szer[i]) for i, c_point in enumerate(coords_pts)]
    c_db_len = addr_phrs_dict["C_LEN"]
    c_adr_phr = ""

    for i, c_point in enumerate(coords_pts):
        fin_dist = 10 ** 6
        fin_idx = 0

        for j, geojson in enumerate(top10_geojson[i]):
            c_poly = ogr.CreateGeometryFromJson(geojson)
            c_poly.Transform(coord_trans)
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
        c_pts_sp = addr_phrs_dict["LIST"][c_inds]
        c_adr_phr += " " + " ".join(c_pts_sp)

        # Uzupelniamy liste dodatkowych informacji o adresie
        c_dod_inf = pow_bubd_arr[pow_bubd_ids, 3]

        # Jeżeli najkrotszy znaleziony dystans jest krótszy niż maksymalna zakladana odleglosc punktu adresowego PRG od
        # budynku BDOT10k to przypisujemy dany budynek do punktu adresowego
        if fin_dist < max_dist:
            bdot10k_dist[c_inds] = fin_dist
            bdot10k_ids[c_inds] = pow_bubd_arr[pow_bubd_ids, 0]

            if len(c_dod_inf) > 0:
                dod_opis_list[c_inds] = c_dod_inf
                c_dod_str = unidecode(c_dod_inf).upper()
                c_adr_phr += " " + str(c_pts_sp[0]) + " " + c_dod_str + " " + str(c_pts_sp[1])

                for inf in c_dod_str.replace(", ", " ").split(" "):
                    if inf not in addr_phrs_dict["UNIQUES"]:
                        addr_phrs_dict["UNIQUES"] += inf + " "

        c_adr_phr += " [" + str(c_db_len + c_inds + 1) + "]\n"

    # Uzupelniamy liste podstawowych i dodatkowych informacji o adresie
    c_addr_arr[0] += c_adr_phr


@lru_cache
def get_corr_reg_name(curr_name):
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
