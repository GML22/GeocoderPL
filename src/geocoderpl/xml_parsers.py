from abc import ABC, abstractmethod
from io import BytesIO

from db_classes import PRG
from geo_utilities import *


class XmlParser(ABC):
    def __init__(self, xml_path: str, tags_tuple: tuple, event_type: str) -> None:
        self.xml_path = xml_path
        self.tags_tuple = tags_tuple
        self.event_type = event_type

    @property
    def get_xml_path(self) -> str:
        return f"{self.xml_path}"

    @abstractmethod
    def check_path(self) -> None:
        pass

    @abstractmethod
    def parse_xml(self) -> None:
        pass


class BDOT10kDictsParser(XmlParser):
    def __init__(self, xml_path: str, tags_tuple: tuple, event_type: str) -> None:
        super().__init__(xml_path, tags_tuple, event_type)
        self.bdot10k_dicts = {}
        self.check_path()
        self.parse_xml()

    def check_path(self) -> None:
        """" Method that checks if path to file is valid """

        if not os.path.isfile(self.xml_path):
            raise Exception("Pod adresem: '" + self.xml_path + "' nie ma pliku '" + os.environ['BDOT10K_DICTS_NAME'] +
                            "'. Uzupełnij ten plik i uruchom program ponownie!")

    def parse_xml(self) -> None:
        """ Method that parses xml file to dictionairy object """

        xml_contex = etree.iterparse(self.xml_path, events=(self.event_type,), tag=self.tags_tuple)
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
                self.bdot10k_dicts[curr_attrib['name']] = curr_dict

    def get_bdot10k_dicts(self) -> dict:
        """ Method that returns final dicts """
        return self.bdot10k_dicts


class BDOT10kDataParser(XmlParser):
    def __init__(self, xml_path: str, tags_tuple: tuple, event_type: str, dicts_tags: dict, tags_dict: dict) -> None:
        super().__init__(xml_path, tags_tuple, event_type)
        self.dicts_tags = dicts_tags
        self.tags_dict = tags_dict
        self.check_path()
        self.bdot10k_dicts = read_bdot10k_dicts()
        self.parse_xml()

    def check_path(self) -> None:
        """" Method that checks if path to file is valid """
        if not os.path.isfile(self.xml_path):
            raise Exception("Pod adresem: '" + self.xml_path + "' nie ma pliku '" + os.environ['BDOT10K_NAME'] +
                            "'. Pobierz ten plik ze strony: '" + os.environ['BDOT10K_LINK'] + "' i uruchom program" +
                            " ponownie!")

    def parse_xml(self) -> None:
        """ Method that parses xml file and saves data to SQL database """

        with zipfile.ZipFile(self.xml_path, "r") as zfile:
            for woj_name in zfile.namelist():
                woj_zip = BytesIO(zfile.read(woj_name))
                logging.info(woj_name)
                bdot10k_woj_rows = []

                with zipfile.ZipFile(woj_zip, "r") as zfile2:
                    for pow_name in zfile2.namelist():
                        pow_zip = BytesIO(zfile2.read(pow_name))
                        with zipfile.ZipFile(pow_zip, "r") as zfile3:
                            for xml_file in zfile3.namelist():
                                if "BUBD" in xml_file:
                                    # Wyciągamy interesujące nas informacje z pliku xml i zapisujemy je w tablicy
                                    bd_xml = BytesIO(zfile3.read(xml_file))
                                    xml_contex = etree.iterparse(bd_xml, events=(self.event_type,), tag=self.tags_tuple)
                                    fin_row = ['', '', '', '', 0, 0, '', 0.0, 0.0, 0.0, '']
                                    bdot10k_woj_rows += self.parse_bdot10k_xml(xml_contex, fin_row)

                # Zapisujemy do bazy danych informacje dotyczące budynkow z danego województwa
                bdot10k_rows = []
                db_save_freq = int(os.environ['DB_SAVE_FREQ'])

                with sa.orm.Session(SQL_ENGINE) as session:
                    for i, c_row in enumerate(bdot10k_woj_rows):
                        bdot10k_rows.append(BDOT10K(*c_row))

                        if i % db_save_freq == 0:
                            session.bulk_save_objects(bdot10k_rows)
                            session.commit()
                            bdot10k_rows = []

                    if bdot10k_rows:
                        session.bulk_save_objects(bdot10k_rows)
                        session.commit()

    def parse_bdot10k_xml(self, xml_contex: etree.iterparse, fin_row: list) -> list:
        """ Method that exctrats data from BDOT10k XML file """

        # Tworzymy liste przechowujaca dane z XML o powiatach
        bdot10k_pow_rows = []
        all_tags = self.tags_tuple

        for _, curr_node in xml_contex:
            c_tag = curr_node.tag
            row_idx = self.tags_dict[c_tag]
            c_text = curr_node.text if curr_node.text is not None else ''

            if c_tag == all_tags[7] and c_text is not None and not c_text.isspace():
                # Wczytujemy geometrię WKT
                crds_lst = c_text.split(" ")
                coords_str = "".join([crds_lst[i] + " " + crds_lst[i + 1] + ", " for i in range(0, len(crds_lst), 2)])
                poly_wkt = "POLYGON((" + coords_str[:-2] + "))"
                poly_geom = ogr.CreateGeometryFromWkt(poly_wkt)

                # Wyliczamy powierzchnię budynku mnozac powierzchnie wielokata przez liczbe kondygnacji
                poly_area = poly_geom.GetArea()
                fin_row[-4] = int(poly_area) if fin_row[4] == 0 else int(poly_area * fin_row[4])

                # Konwertujemy współrzędne z układu map polskich do układu map google
                coord_trans = create_coords_transform(int(os.environ["PL_CRDS"]), int(os.environ["WORLD_CRDS"]), True)
                poly_geom.Transform(coord_trans)

                # Wyliczamy centroid wielokata budynku
                poly_centroid = poly_geom.Centroid()
                poly_centr_y = np.asarray(poly_centroid.GetY())
                poly_centr_x = np.asarray(poly_centroid.GetX())
                coords_prec = int(os.environ["COORDS_PREC"])
                fin_row[-3] = np.round(poly_centr_y, coords_prec)
                fin_row[-2] = np.round(poly_centr_x, coords_prec)

                # Konwertujemy geometrie na GeoJson
                geojson_poly = poly_geom.ExportToJson()
                reduced_geojson = reduce_coordinates_precision(geojson_poly, coords_prec)
                fin_row[-1] = reduced_geojson

                # Dodajemy nowy wiersz do lacznej listy
                c_sekt_tpl = get_sector_codes(poly_centr_y, poly_centr_x)
                c_sekt_szer = c_sekt_tpl[0]
                c_sekt_dl = c_sekt_tpl[1]
                kod_sektora = str(c_sekt_szer).zfill(3) + "_" + str(c_sekt_dl).zfill(3)
                fin_row2 = [kod_sektora] + fin_row
                bdot10k_pow_rows.append(fin_row2)
                fin_row = ['', '', '', '', 0, 0, '', 0.0, 0.0, 0.0, '']
            elif c_tag == all_tags[5]:
                fin_row[row_idx] = 1 if c_text == 'true' else 0
            elif c_tag == all_tags[4]:
                fin_row[row_idx] = int(c_text) if c_text.isnumeric() else 0
            elif c_tag in (all_tags[0], all_tags[1], all_tags[2], all_tags[3]):
                c_dict = self.bdot10k_dicts[self.dicts_tags[c_tag]]

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


@time_decorator
def read_bdot10k_dicts() -> dict:
    """ Function that reads BDOT10K dicts into dictionairy"""

    # Parsujemy plik XML do postaci słowika
    dicts_path = os.path.join(os.environ["PARENT_PATH"], os.environ['SLOWS_PATH'])
    all_tags = tuple(os.environ['BDOT10K_DICTS_TAGS'].split(";"))
    bdot10k_dicts = BDOT10kDictsParser(dicts_path, all_tags, 'start').get_bdot10k_dicts()

    # Importujemy inne słowniki niezawarte w domyślnym zestawie słowników
    bubd_codes_path = os.path.join(os.environ["PARENT_PATH"], os.environ['BUBD_CODES_PATH'])
    bdot10k_dicts["x_kod"] = csv_to_dict(bubd_codes_path)

    # Importujemy inne słowniki niezawarte w domyślnym zestawie słowników
    karto10k_path = os.path.join(os.environ["PARENT_PATH"], os.environ['KARTO10K_PATH'])
    bdot10k_dicts["x_kodKarto10k"] = csv_to_dict(karto10k_path)
    return bdot10k_dicts


class PRGDataParser(XmlParser):
    def __init__(self, xml_path: str, tags_tuple: tuple, event_type: str, perms_dict: dict) -> None:
        super().__init__(xml_path, tags_tuple, event_type)
        self.perms_dict = perms_dict
        self.check_path()
        self.addr_phrs_list = []
        self.addr_phrs_len = 0
        self.parse_xml()

    def check_path(self) -> None:
        """" Method that checks if path to file is valid """
        if not os.path.isfile(self.xml_path):
            raise Exception("Pod adresem: '" + self.xml_path + "' nie ma pliku '" + os.environ['PRG_NAME'] +
                            "'. Pobierz ten plik ze strony: '" + os.environ['PRG_LINK'] +
                            "' i uruchom program ponownie!")

    def parse_xml(self) -> None:
        """ Method that parses xml file and saves data to SQL database """

        # Definiujemy podstawowe parametry
        x_path, x_filename = os.path.split(self.xml_path)
        curr_dir = os.getcwd()
        os.chdir(x_path)
        woj_names = []

        try:
            with zipfile.ZipFile(x_filename, "r") as zfile:
                woj_names = zfile.namelist()
                zfile.extractall()

            for woj_name in woj_names:
                # Wczytujemy dane XML dla danego wojewodztwa
                xml_contex = etree.iterparse(woj_name, events=(self.event_type,), tag=self.tags_tuple[:-1])

                # Tworzymy listę punktów adresowych PRG
                points_list = self.create_points_list(xml_contex)

                # Konwertujemy wspolrzedne PRG z ukladu polskiego do ukladu mag Google i sprawdzamy czy leżą one
                # wewnątrz shapefile'a swojej gminy
                self.check_prg_pts_add_db(points_list, woj_name)

        finally:
            os.chdir(curr_dir)

            if woj_names:
                [os.remove(file1) for file1 in os.listdir('.') if file1 in woj_names]

    def create_points_list(self, xml_contex: etree.iterparse) -> list:
        """ Creating list of data points """

        # Definiujemy podstawowe parametry
        c_ind = 0
        c_row = [''] * 11
        points_list = [list() for _ in range(len(c_row))]
        coords_prec = int(os.environ["COORDS_PREC"])
        all_tags = self.tags_tuple
        num_dict = {all_tags[1]: 3, all_tags[2]: 4, all_tags[3]: 5, all_tags[4]: 6, all_tags[5]: 7, all_tags[6]: 8}
        rep_dict = {"ul. ": "", "ulica ": "", "al.": "Aleja", "Al.": "Aleja", "pl.": "Plac", "Pl.": "Plac",
                    "wTrakcieBudowy": "w trakcie budowy"}
        rep_dict_keys = np.asarray(list(rep_dict.keys()))

        with sa.orm.Session(SQL_ENGINE) as session:
            addr_phrs_uniq = session.query(UniqPhrs.uniq_phrs).all()[0][0]

        for _, curr_node in xml_contex:
            c_val = curr_node.text
            c_tag = curr_node.tag

            if c_tag == all_tags[0] and c_val != "Polska":
                c_row[c_ind] = c_val
                c_ind += 1
            elif c_tag in [all_tags[1], all_tags[2], all_tags[3], all_tags[4], all_tags[5], all_tags[6]]:
                c_val = c_val if c_val is not None else ""
                sub_in = [substring in c_val for substring in rep_dict_keys]

                if sum(sub_in) > 0:
                    c_key = rep_dict_keys[sub_in][0]
                    c_val = c_val.replace(c_key, rep_dict[c_key])

                c_row[num_dict[c_tag]] = c_val
                c_ind = 0
            elif c_tag == all_tags[7] or c_tag == all_tags[8]:
                c_val = c_val.split()
                c_row[-2:] = [round(float(c_val[0]), coords_prec), round(float(c_val[1]), coords_prec)]

                if c_row[0] != '' and c_row[1] != '' and c_row[2] != '':
                    [points_list[i].append(el) for i, el in enumerate(c_row)]

                    uniq_addr, uniq_ids = np.unique(np.asarray([unidecode(c_row[i]).upper() for i in (3, 4, 5, 6, 7)
                                                                if c_row[i] != ""]), return_index=True)
                    addr_arr = uniq_addr[np.argsort(uniq_ids)]
                    self.addr_phrs_list.append(addr_arr[self.perms_dict[len(addr_arr)]].tolist())

                    for el in addr_arr:
                        if el not in addr_phrs_uniq:
                            addr_phrs_uniq += el + " "

                c_ind = 0
                c_row = [''] * 11

            # Czyscimy przetworzone obiekty wezlow XML z pamieci
            clear_xml_node(curr_node)

        with sa.orm.Session(SQL_ENGINE) as session:
            session.query(UniqPhrs).filter(UniqPhrs.uniq_id == 1).update({'uniq_phrs': addr_phrs_uniq})
            session.commit()

        return points_list

    @time_decorator
    def check_prg_pts_add_db(self, points_list: list, woj_name: str):
        """ Function that converts spatial reference of PRG points from 2180 to 4326, checks if given PRG point belongs
        to shapefile of its district and finds closest building shape for given PRG point """

        # Konwertujemy wpółrzędne do oczekiwanego układu wspolrzednych 4326 i dodajemy do bazy danych kolumny
        # zawierajace przekonwertowane wspolrzedne
        trans_crds = np.zeros((2, len(points_list[0])), dtype=np.float64)
        trans_crds[:] = convert_coords(points_list[-2:], os.environ['PL_CRDS'], os.environ['WORLD_CRDS'])
        trans_crds = trans_crds.T

        # Grupujemy kolumny z nazwami powiatow oraz gmin i sprawdzamy czy punkty adresowe z bazy PRG znajduja sie
        # wewnatrz shapefili ich gmin
        df_regions = pd.DataFrame({'POWIAT': points_list[1], 'GMINA': points_list[2]})
        grouped_regions = df_regions.groupby(['POWIAT', 'GMINA'], as_index=False).groups

        # Tworzymy inne przydatne obiekty
        woj_idx = woj_name.rfind("_") + 1
        woj_name = unidecode(woj_name[woj_idx:-4].upper())
        pts_lst_len = len(points_list[0])
        zrodlo_list = ['PRG'] * pts_lst_len
        popraw_list = [1] * pts_lst_len
        dists_list = [0.0] * pts_lst_len
        bdot10k_ids = np.zeros(pts_lst_len, dtype=int)
        bdot10k_dist = np.zeros(pts_lst_len)
        sekt_kod_list = np.full(pts_lst_len, fill_value='', dtype='<U7')
        dod_opis_list = np.full(pts_lst_len, fill_value='', dtype=object)

        # Dla każdej gminy i powiatu sprawdzamy czy punkty do nich przypisane znajduja sie wewnatrz wielokata danej
        # gminy oraz znajdujemy najbliższy budynek do danego punktu PRG
        points_inside_polygon(grouped_regions, woj_name, trans_crds, points_list, popraw_list, dists_list, zrodlo_list,
                              bdot10k_ids, bdot10k_dist, sekt_kod_list, dod_opis_list, self.addr_phrs_list,
                              self.addr_phrs_len)

        # Zapisujemy do bazy danych informacje dotyczące budynkow z danego województwa
        prg_rows = []
        db_save_freq = int(os.environ['DB_SAVE_FREQ'])

        with sa.orm.Session(SQL_ENGINE) as session:
            for i in range(pts_lst_len):
                prg_rows.append(PRG(*[lst[i] for lst in points_list[:-2]], trans_crds[i, 0], trans_crds[i, 1],
                                    zrodlo_list[i], popraw_list[i], dists_list[i], bdot10k_ids[i], bdot10k_dist[i],
                                    sekt_kod_list[i], dod_opis_list[i]))
                if i % db_save_freq == 0:
                    session.bulk_save_objects(prg_rows)
                    session.commit()
                    prg_rows = []

            if prg_rows:
                session.bulk_save_objects(prg_rows)
                session.commit()

        self.addr_phrs_len += pts_lst_len
        self.addr_phrs_list = []
