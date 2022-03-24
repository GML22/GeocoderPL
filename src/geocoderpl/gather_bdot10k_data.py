""" Module that gathers BDOT10K buildings polygons into SQL database """

import pandas as pd
import sqlalchemy as sa

from geo_utilities import *
from xml_parser import BDOT10kDictsParser, BDOT10kDataParser


@time_decorator
def create_bdot10k_table(sql_engine: sa.engine) -> None:
    """ Function that gathers BDOT10K BUBD polygons into SQL database """

    # Wczytujemy niezbędne słowniki BDOT10K
    bdot10k_dicts = read_bdot10k_dicts()

    # Otwieramy plik ".zip" BDOT10K i parsujemy XMLe
    open_bdot10k_parse_xml(bdot10k_dicts, sql_engine)


@time_decorator
def read_bdot10k_dicts() -> dict:
    """ Function that reads BDOT10K dicts into dictionairy"""

    # Parsujemy plik XML do postaci słowika
    dicts_path = os.path.join(os.environ["PARENT_PATH"], os.environ['SLOWS_PATH'])
    all_tags = tuple(os.environ['BDOT10K_DICTS_TAGS'].split(";"))
    bdot10k_dicts = BDOT10kDictsParser(dicts_path, all_tags, 'OT_BDOT10k_Slowniki.xsd', 'start').get_bdot10k_dicts()

    # Importujemy inne słowniki niezawarte w domyślnym zestawie słowników
    bubd_codes_path = os.path.join(os.environ["PARENT_PATH"], os.environ['BUBD_CODES_PATH'])
    bdot10k_dicts["x_kod"] = csv_to_dict(bubd_codes_path)

    # Importujemy inne słowniki niezawarte w domyślnym zestawie słowników
    karto10k_path = os.path.join(os.environ["PARENT_PATH"], os.environ['KARTO10K_PATH'])
    bdot10k_dicts["x_kodKarto10k"] = csv_to_dict(karto10k_path)
    return bdot10k_dicts


def csv_to_dict(c_path: str) -> dict:
    """ Function that imports CSV file and creates dictionairy from first two columns of that file """

    try:
        x_kod = pd.read_csv(c_path, sep=";", dtype=str, engine='c', header=None, low_memory=False).values
    except FileNotFoundError:
        raise Exception("Pod adresem: '" + c_path + "' nie ma pliku potrzebnego pliku. Uzupełnij ten plik i  uruchom " +
                        "program ponownie!")
    return {row[0]: row[1] for row in x_kod}


@time_decorator
def open_bdot10k_parse_xml(bdot10k_dicts: dict, sql_engine: sa.engine) -> None:
    """ Opening zipped BDOT10K database, parsing xml files and inserting rows into db """

    # Definiujemy podstawowe tagi
    m_tags = os.environ['BDOT10K_TAGS'].split(";")
    all_tags = (m_tags[0], m_tags[1], m_tags[2], m_tags[3], m_tags[4], m_tags[5], m_tags[6], m_tags[7])
    dicts_tags = {m_tags[0]: m_tags[-4], m_tags[1]: m_tags[-3], m_tags[2]: m_tags[-2], m_tags[3]: m_tags[-1]}
    tags_dict = {tag: i for i, tag in enumerate(all_tags)}
    bdot10k_path = os.path.join(os.environ["PARENT_PATH"], os.environ['BDOT10K_PATH'])
    BDOT10kDataParser(bdot10k_path, all_tags, 'Polska_GML.zip', 'end', bdot10k_dicts, dicts_tags, tags_dict,
                      sql_engine, 'https://opendata.geoportal.gov.pl/bdot10k/Polska_GML.zip')
