""" Module that gathers PRG address points into SQL database """

import pickle
import zipfile
from io import BytesIO

import numpy as np
import sqlalchemy as sa
from lxml import etree
from sqlalchemy.orm import declarative_base
from unidecode import unidecode

from geo_utilities import time_decorator, clear_xml_node
from super_permutations import SuperPerms
from valid_prg_points import check_prg_points


@time_decorator
def create_prg_table(regs_dict: dict, sql_engine: sa.engine) -> None:
    """ Function that gathers PRG address points into SQL database """

    # Tworzymy pusta baze danych PRG_TABLE
    base_prg.metadata.create_all(sql_engine)

    # Otwieramy zzipowana baze PRG, parsujemy znajdujace sie w srodku xmle i zapisujemy punkty adresowe PRG do bazy
    open_zip_parse_xml(regs_dict, sql_engine)


@time_decorator
def open_zip_parse_xml(regs_dict: dict, sql_engine: sa.engine) -> None:
    """ Opening zipped PRG database, parsing xml files and inserting rows into db """

    perms_dict = get_super_permut_dict(int(os.environ['SUPPERM_MAX']))
    sekt_num = int(os.environ["SEKT_NUM"])
    addr_arr = np.empty((sekt_num, sekt_num, 1), dtype=object)
    addr_arr[...] = ''
    addr_phrs_d = {"LIST": [], "ADDR_ARR": addr_arr, "C_LEN": 0, "UNIQUES": ""}
    prg_path = os.path.join(os.environ["PARENT_PATH"], os.environ['PRG_PATH'])

    try:
        with zipfile.ZipFile(prg_path, "r") as zfile:
            for woj_name in zfile.namelist():
                xml_file = BytesIO(zfile.read(woj_name))
                t1 = '{urn:gugik:specyfikacje:gmlas:panstwowyRejestrGranicAdresy:1.0}jednostkaAdmnistracyjna'
                t2 = '{urn:gugik:specyfikacje:gmlas:panstwowyRejestrGranicAdresy:1.0}miejscowosc'
                t3 = '{urn:gugik:specyfikacje:gmlas:panstwowyRejestrGranicAdresy:1.0}czescMiejscowosci'
                t4 = '{urn:gugik:specyfikacje:gmlas:panstwowyRejestrGranicAdresy:1.0}ulica'
                t5 = '{urn:gugik:specyfikacje:gmlas:panstwowyRejestrGranicAdresy:1.0}numerPorzadkowy'
                t6 = '{urn:gugik:specyfikacje:gmlas:panstwowyRejestrGranicAdresy:1.0}kodPocztowy'
                t7 = '{urn:gugik:specyfikacje:gmlas:panstwowyRejestrGranicAdresy:1.0}status'
                t8 = '{http://www.opengis.net/gml/3.2}pos'
                t9 = 'pos'
                xml_contex = etree.iterparse(xml_file, events=('end',), tag=(t1, t2, t3, t4, t5, t6, t7, t8))

                # Tworzymy listę punktów
                points_arr = create_points_list(xml_contex, t1, t2, t3, t4, t5, t6, t7, t8, t9, perms_dict, addr_phrs_d)

                # Konwertujemy wspolrzedne PRG z ukladu polskiego do ukladu mag Google i sprawdzamy czy leżą one
                # wewnątrz shapefile'a swojej gminy
                fin_points_list = check_prg_points(points_arr, regs_dict, woj_name, addr_phrs_d)

                # Zapisujemy do bazy danych informacje dotyczące budynkow z danego województwa
                with sa.orm.Session(sql_engine) as session:
                    session.bulk_save_objects(fin_points_list)
                    session.commit()

                addr_phrs_dict["C_LEN"] += len(fin_points_list)
                addr_phrs_dict["LIST"] = []
    except FileNotFoundError:
        raise Exception("Pod podanym adresem: '" + prg_path + "' nie ma pliku 'PRG-punkty_adresowe.zip'. Pobierz ten" +
                        " plik ze strony: 'https://dane.gov.pl/pl/dataset/726,panstwowy-rejestr-granic-i-powierzchni" +
                        "-jednostek-podziaow-terytorialnych-kraju/resource/29538' i uruchom program ponownie!")

    # Usuwamy zbędne obiekty ze słownika
    addr_phrs_d.pop("LIST", None)
    addr_phrs_d.pop("C_LEN", None)

    # Zapisujemy zbiór unikalnych adresow na dysku twardym
    with open(os.path.join(fls_path, "all_address_phrases.obj"), 'wb') as f:
        pickle.dump(addr_phrs_dict, f, pickle.HIGHEST_PROTOCOL)


def get_super_permut_dict(max_len: int) -> dict:
    """ Function that creates indices providing superpermutations for lists of strings with length of maximum 5
    elements """

    return {i: SuperPerms(i).fin_super_perm_ids for i in range(1, max_len + 1)}


def create_points_list(xml_contex: lxml.etree.iterparse, t1: str, t2: str, t3: str, t4: str, t5: str, t6: str, t7: str,
                       t8: str, t9: str, perms_dict: dict, addr_phrs_dict: dict) -> np.ndarray:
    """ Creating list of data points """

    c_row = [''] * 11
    points_list = []
    c_ind = 0
    num_dict = {t2: 3, t3: 4, t4: 5, t5: 6, t6: 7, t7: 8}
    rep_dict = {"ul. ": "", "ulica ": "", "al.": "Aleja", "Al.": "Aleja", "pl.": "Plac", "Pl.": "Plac",
                "wTrakcieBudowy": "w trakcie budowy"}
    rep_dict_keys = np.asarray(list(rep_dict.keys()))

    for _, curr_node in xml_contex:
        c_val = curr_node.text
        c_tag = curr_node.tag

        if c_tag == t1 and c_val != "Polska":
            c_row[c_ind] = c_val
            c_ind += 1
        elif c_tag in [t2, t3, t4, t5, t6, t7]:
            c_val = c_val if c_val is not None else ""
            sub_in = [substring in c_val for substring in rep_dict_keys]

            if sum(sub_in) > 0:
                c_key = rep_dict_keys[sub_in][0]
                c_val = c_val.replace(c_key, rep_dict[c_key])

            c_row[num_dict[c_tag]] = c_val
            c_ind = 0
        elif c_tag == t8 or c_tag == t9:
            c_val = c_val.split()
            c_row[-2:] = [str(round(float(c_val[0]), coords_prec)), str(round(float(c_val[1]), coords_prec))]

            if c_row[0] != '' and c_row[1] != '' and c_row[2] != '':
                points_list.append(c_row)
                uniq_addr, uniq_ids = np.unique(np.asarray([unidecode(c_row[i]).upper() for i in (3, 4, 5, 6, 7)
                                                            if c_row[i] != ""]), return_index=True)
                addr_arr = uniq_addr[np.argsort(uniq_ids)]
                addr_phrs_dict["LIST"].append(addr_arr[perms_dict[len(addr_arr)]].tolist())

                for el in addr_arr:
                    if el not in addr_phrs_dict["UNIQUES"]:
                        addr_phrs_dict["UNIQUES"] += el + " "

            c_ind = 0
            c_row = [''] * 11

        # Czyscimy przetworzone obiekty wezlow XML z pamieci
        clear_xml_node(curr_node)

    return np.asarray(points_list)
