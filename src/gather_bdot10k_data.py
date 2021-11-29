""" Module that gathers BDOT10K buildings polygons into SQL database """
import re
import zipfile
from io import BytesIO

import numpy as np
import pandas as pd
from lxml import etree

from geo_utilities import *


@time_decorator
def create_bdot10k_table(fls_path, lyrs_path, coords_prec, curr_conn, cursor, sekt_num):
    """ Function that gathers BDOT10K BUBD polygons into SQL database """

    # Wczytujemy niezbędne słowniki BDOT10K
    bdot10k_dicts = read_bdot10k_dicts(lyrs_path, fls_path)

    # Tworzymy pusta baze danych BDOT10K_TABLE
    cursor.execute("CREATE TABLE IF NOT EXISTS BDOT10K_TABLE(" +
                   "BDOT10K_BUBD_ID integer PRIMARY KEY, " +
                   "KOD_SEKTORA text NOT NULL, " +
                   "KATEGORIA_BUDYNKU text NOT NULL, " +
                   "NAZWA_KARTOGRAFICZNA text NOT NULL, " +
                   "STAN_BUDYNKU text NOT NULL, " +
                   "FUNKCJA_BUDYNKU text NOT NULL, " +
                   "LICZBA_KONDYGNACJI real NOT NULL, " +
                   "CZY_ZABYTEK integer NOT NULL, " +
                   "OPIS_BUDYNKU text NOT NULL, " +
                   "POWIERZCHNIA real NOT NULL, " +
                   "CENTROID_LAT real NOT NULL, " +
                   "CENTROID_LONG real NOT NULL, " +
                   "BUBD_GEOJSON text NOT NULL)")

    # Tworzymy indeks, który przyspieszy kwerendy WHERE dla sektorow
    cursor.execute("CREATE INDEX idx_sector_code ON BDOT10K_TABLE(KOD_SEKTORA)")

    # Otwieramy plik ".zip" BDOT10K i parsujemy XMLe
    open_bdot10k_parse_xml(lyrs_path, bdot10k_dicts, coords_prec, cursor, curr_conn, sekt_num)


@time_decorator
def read_bdot10k_dicts(lyrs_path, fls_path):
    """ Function that reads BDOT10K dicts into dictionairy"""

    # Parsujemy XMLa
    dicts_path = lyrs_path + "BDOT10K\\OT_BDOT10k_Slowniki.xsd"
    assrt_msg = "W folderze '" + lyrs_path + "\\BDOT10K' brakuje pliku 'OT_BDOT10k_Slowniki.xsd'. Uzupełnij ten " + \
                "plik i uruchom program ponownie!"
    assert os.path.exists(dicts_path), assrt_msg

    t1 = '{http://www.opengis.net/gml/3.2}description'
    t2 = '{http://www.w3.org/2001/XMLSchema}enumeration'
    t3 = '{http://www.w3.org/2001/XMLSchema}simpleType'
    xml_contex = etree.iterparse(dicts_path, events=('start',), tag=(t1, t2, t3))
    bdot10k_dicts = {}
    curr_dict = {}
    c_val = ""

    for _, curr_node in xml_contex:
        c_text = curr_node.text
        curr_attrib = curr_node.attrib

        if not c_text.isspace() and c_text is not None:
            c_text1 = "".join([lett if not lett.isupper() else " " + lett.lower() for i, lett in enumerate(c_text)])
            curr_dict[c_val] = c_text1

        if 'value' in curr_attrib:
            c_val = curr_attrib['value']

        if 'name' in curr_attrib:
            curr_dict = {}
            bdot10k_dicts[curr_attrib['name']] = curr_dict

    # Importujemy inne słowniki niezawarte w domyślnym zestawie słowników
    bubd_codes_path = fls_path + "x_kod.txt"
    assrt_msg1 = "W folderze '" + fls_path + "' brakuje pliku 'x_kod.txt'. Uzupełnij ten plik i uruchom program " + \
                 "ponownie!"
    assert os.path.exists(bubd_codes_path), assrt_msg1

    bdot10k_dicts["x_kod"] = csv_to_dict(bubd_codes_path)

    # Importujemy inne słowniki niezawarte w domyślnym zestawie słowników
    karto10k_path = fls_path + "x_kodKarto10k.txt"
    assrt_msg2 = "W folderze '" + fls_path + "' brakuje pliku 'x_kodKarto10k.txt'. Uzupełnij ten plik i uruchom " + \
                 "program ponownie!"
    assert os.path.exists(karto10k_path), assrt_msg2
    bdot10k_dicts["x_kodKarto10k"] = csv_to_dict(karto10k_path)

    return bdot10k_dicts


def csv_to_dict(file_path):
    """ Function that imports CSV file and creates dictionairy from first two columns of that file """
    x_kod = pd.read_csv(file_path, sep=";", dtype=str, engine='c', header=None, low_memory=False).values
    return {row[0]: row[1] for row in x_kod}


@time_decorator
def open_bdot10k_parse_xml(lyrs_path, bdot10k_dicts, coords_prec, cursor, curr_conn, sekt_num):
    """ Opening zipped BDOT10K database, parsing xml files and inserting rows into db """

    bdot10k_path = lyrs_path + "BDOT10K\\Polska_GML.zip"
    assrt_msg = "W folderze '" + lyrs_path + "\\BDOT10K' brakuje pliku 'Polska_GML.zip'. Uzupełnij ten plik i " + \
                "uruchom program ponownie!"
    assert os.path.exists(bdot10k_path), assrt_msg

    t0 = "{urn:gugik:specyfikacje:gmlas:bazaDanychObiektowTopograficznych10k:1.0}x_kod"
    t1 = "{urn:gugik:specyfikacje:gmlas:bazaDanychObiektowTopograficznych10k:1.0}x_skrKarto"
    t2 = "{urn:gugik:specyfikacje:gmlas:bazaDanychObiektowTopograficznych10k:1.0}x_katIstnienia"
    t3 = "{urn:gugik:specyfikacje:gmlas:bazaDanychObiektowTopograficznych10k:1.0}funSzczegolowaBudynku"
    t4 = "{urn:gugik:specyfikacje:gmlas:bazaDanychObiektowTopograficznych10k:1.0}liczbaKondygnacji"
    t5 = "{urn:gugik:specyfikacje:gmlas:bazaDanychObiektowTopograficznych10k:1.0}zabytek"
    t6 = "{urn:gugik:specyfikacje:gmlas:bazaDanychObiektowTopograficznych10k:1.0}x_informDodatkowa"
    t7 = "{http://www.opengis.net/gml/3.2}posList"
    all_tags = (t0, t1, t2, t3, t4, t5, t6, t7)
    tags_dict = {tag: i for i, tag in enumerate(all_tags)}
    dicts_tags = {t0: 'x_kod', t1: 'OT_SkrKartoType', t2: 'OT_KatIstnieniaType', t3: 'OT_FunSzczegolowaBudynkuType'}

    with zipfile.ZipFile(bdot10k_path, "r") as zfile:
        for woj_name in zfile.namelist():
            woj_zip = BytesIO(zfile.read(woj_name))
            print("\n" + woj_name + ": " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
            bdot10k_woj_rows = []

            with zipfile.ZipFile(woj_zip, "r") as zfile2:
                for pow_name in zfile2.namelist():
                    pow_zip = BytesIO(zfile2.read(pow_name))
                    with zipfile.ZipFile(pow_zip, "r") as zfile3:
                        for xml_file in zfile3.namelist():
                            if "BUBD" in xml_file:
                                # Wyciągamy interesujące nas informacje z pliku xml i zapisujemy je w tablicy
                                bdot10k_pow_rows = extract_xml_info(zfile3, xml_file, all_tags, tags_dict, dicts_tags,
                                                                    bdot10k_dicts, coords_prec, t0, t1, t2, t3, t4, t5,
                                                                    t7, sekt_num)
                                bdot10k_woj_rows += bdot10k_pow_rows

            # Zapisujemy do bazy danych informacje dotyczące budynkow z danego województwa
            cursor.executemany("""INSERT INTO BDOT10K_TABLE(KOD_SEKTORA, KATEGORIA_BUDYNKU, NAZWA_KARTOGRAFICZNA, """ +
                               """STAN_BUDYNKU, FUNKCJA_BUDYNKU, LICZBA_KONDYGNACJI, CZY_ZABYTEK, OPIS_BUDYNKU, """ +
                               """POWIERZCHNIA, CENTROID_LAT, CENTROID_LONG, BUBD_GEOJSON) """ +
                               """values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", bdot10k_woj_rows)
            curr_conn.commit()


def extract_xml_info(zfile3, xml_file, all_tags, tags_dict, dicts_tags, bdot10k_dicts, coords_prec, t0, t1, t2, t3, t4,
                     t5, t7, sekt_num):
    """ Function that extracts useful information about buildings from xml files of districts """

    bubd_xml = BytesIO(zfile3.read(xml_file))
    xml_contex = etree.iterparse(bubd_xml, events=('end',), tag=all_tags)
    bdot10k_pow_rows = []
    fin_row = ['', '', '', '', 0, 0, '', 0.0, 0.0, 0.0, '']

    for _, curr_node in xml_contex:
        c_tag = curr_node.tag
        row_idx = tags_dict[c_tag]
        c_text = curr_node.text if curr_node.text is not None else ''

        if c_tag == t7 and c_text is not None and not c_text.isspace():
            # Wczytujemy geometrię WKT
            coords_list = c_text.split(" ")
            coords_str = "".join([coords_list[i] + " " + coords_list[i + 1] + ", " for i in
                                  range(0, len(coords_list), 2)])

            poly_wkt = "POLYGON((" + coords_str[:-2] + "))"
            poly_geom = ogr.CreateGeometryFromWkt(poly_wkt)

            # Wyliczamy powierzchnię budynku mnozac powierzchnie wielokata przez liczbe kondygnacji
            poly_area = poly_geom.GetArea()
            fin_row[-4] = int(poly_area) if fin_row[4] == 0 else int(poly_area * fin_row[4])

            # Konwertujemy współrzędne z układu 2180 do 4326
            coord_trans = create_coords_transform(2180, 4326, True)
            poly_geom.Transform(coord_trans)

            # Wyliczamy centroid wielokata budynku
            poly_centroid = poly_geom.Centroid()
            poly_centr_y = np.asarray(poly_centroid.GetY())
            poly_centr_x = np.asarray(poly_centroid.GetX())
            fin_row[-3] = np.round(poly_centr_y, coords_prec)
            fin_row[-2] = np.round(poly_centr_x, coords_prec)

            # Konwertujemy geometrie na GeoJson
            geojson_poly = poly_geom.ExportToJson()
            reduced_geojson = reduce_coordinates_precision(geojson_poly, coords_prec)
            fin_row[-1] = reduced_geojson

            # Dodajemy nowy wiersz do lacznej listy
            c_sekt_szer, c_sekt_dl = get_sector_codes(poly_centr_y, poly_centr_x, sekt_num)
            kod_sektora = str(c_sekt_szer).zfill(3) + "_" + str(c_sekt_dl).zfill(3)
            bdot10k_pow_rows.append([kod_sektora] + fin_row)
            fin_row = ['', '', '', '', 0, 0, '', 0.0, 0.0, 0.0, '']

        elif c_tag == t5:
            fin_row[row_idx] = 1 if c_text == 'true' else 0
        elif c_tag == t4:
            fin_row[row_idx] = int(c_text) if c_text.isnumeric() else 0
        elif c_tag in (t0, t1, t2, t3):
            c_dict = bdot10k_dicts[dicts_tags[c_tag]]

            if c_text in c_dict:
                if fin_row[row_idx] == '':
                    fin_row[row_idx] = c_dict[c_text]
                else:
                    fin_row[row_idx] += " | " + c_dict[c_text]
            else:
                fin_row[row_idx] = ""
        else:
            fin_row[row_idx] = c_text

        # Czyscimy przetworzone obiekty wezlow XML z pamieci
        clear_xml_node(curr_node)

    return bdot10k_pow_rows


def reduce_coordinates_precision(geojson_poly, precision):
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
