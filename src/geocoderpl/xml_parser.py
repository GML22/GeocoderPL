import zipfile
from abc import ABC, abstractmethod
from io import BytesIO

import sqlalchemy as sa
from lxml import etree
from osgeo import ogr

from db_classes import BDOT10K
from geo_utilities import *


class XmlParser(ABC):
    def __init__(self, xml_path: str, tags_tuple: tuple) -> None:
        self.xml_path = xml_path
        self.tags_tuple = tags_tuple

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
    def __init__(self, xml_path: str, tags_tuple: tuple, file_name: str, event_type: str) -> None:
        super().__init__(xml_path, tags_tuple)
        self.filne_name = file_name
        self.event_type = event_type
        self.bdot10k_dicts = {}
        self.check_path()
        self.parse_xml()

    def check_path(self) -> None:
        """" Method that checks if path to file is valid """
        if not os.path.isfile(self.xml_path):
            raise Exception("Pod adresem: '" + self.xml_path + "' nie ma pliku '" + self.file_name + "'. Uzupełnij " +
                            "ten plik i uruchom program ponownie!")

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
    def __init__(self, xml_path: str, tags_tuple: tuple, file_name: str, event_type: str, bdot10k_dicts: dict,
                 dicts_tags: dict, tags_dict: dict, sql_engine: sa.engine, data_link: str) -> None:
        super().__init__(xml_path, tags_tuple)
        self.file_name = file_name
        self.event_type = event_type
        self.bdot10k_dicts = bdot10k_dicts
        self.dicts_tags = dicts_tags
        self.tags_dict = tags_dict
        self.sql_engine = sql_engine
        self.data_link = data_link
        self.check_path()
        self.parse_xml()

    def check_path(self) -> None:
        """" Method that checks if path to file is valid """
        if not os.path.isfile(self.xml_path):
            raise Exception("Pod adresem: '" + self.xml_path + "' nie ma pliku '" + self.file_name + "'. Pobierz ten" +
                            " plik ze strony: '" + self.data_link + "' i uruchom program ponownie!")

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
                                    bubd_xml = BytesIO(zfile3.read(xml_file))
                                    xml_contex = etree.iterparse(bubd_xml, events=(self.event_type,),
                                                                 tag=self.tags_tuple)
                                    fin_row = ['', '', '', '', 0, 0, '', 0.0, 0.0, 0.0, '']
                                    bdot10k_woj_rows += self.parse_bdot10k(xml_contex, fin_row)

                # Zapisujemy do bazy danych informacje dotyczące budynkow z danego województwa
                with sa.orm.Session(self.sql_engine) as session:
                    session.bulk_save_objects(bdot10k_woj_rows)
                    session.commit()

    def parse_bdot10k(self, xml_contex: lxml.etree.iterparse, fin_row: list) -> list:
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
                bdot10k_pow_rows.append(BDOT10K(*fin_row2))
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
