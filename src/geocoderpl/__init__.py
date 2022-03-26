""" __init_.py module """

import logging
import os
import time

import numpy as np
import sqlalchemy as sa

from db_classes import BASE, SQL_ENGINE
from geo_utilities import create_logger, time_decorator, create_regs_dicts, get_super_permut_dict
from xml_parsers import BDOT10kDataParser, PRGDataParser

# Tworzymy domyślny obiekt loggera
create_logger('root')


@time_decorator
def main() -> None:
    """ Main function """

    # Tworzymy słownik kształtów
    regs_dict = create_regs_dicts()

    # Sprawdzamy w bazie czy tablica 'BDOT10K_TABLE' istnieje
    if not sa.inspect(SQL_ENGINE).has_table("BDOT10K_TABLE"):
        # Tworzymy domyslne obiekty tabel BDOT10K i PRG
        BASE.metadata.create_all(SQL_ENGINE)

        # Tworzymy tabelę 'BDOT10K_TABLE' z danymi o budynkach
        m_tags = os.environ['BDOT10K_TAGS'].split(";")
        all_tags = (m_tags[0], m_tags[1], m_tags[2], m_tags[3], m_tags[4], m_tags[5], m_tags[6], m_tags[7])
        dicts_tags = {m_tags[0]: m_tags[-4], m_tags[1]: m_tags[-3], m_tags[2]: m_tags[-2], m_tags[3]: m_tags[-1]}
        tags_dict = {tag: i for i, tag in enumerate(all_tags)}
        bdot10k_path = os.path.join(os.environ["PARENT_PATH"], os.environ['BDOT10K_PATH'])
        BDOT10kDataParser(bdot10k_path, all_tags, 'end', dicts_tags, tags_dict)

        # Tworzymy tabelę SQL z punktami adresowymi PRG
        sekt_num = int(os.environ["SEKT_NUM"])
        addr_arr = np.empty((sekt_num, sekt_num, 1), dtype=object)
        addr_arr[...] = ''
        addr_phrs_d = {"LIST": [], "ADDR_ARR": addr_arr, "C_LEN": 0, "UNIQUES": ""}
        prg_path = os.path.join(os.environ["PARENT_PATH"], os.environ['PRG_PATH'])
        all_tags1 = tuple(os.environ['PRG_TAGS'].split(";"))
        perms_dict = get_super_permut_dict(int(os.environ['SUPPERM_MAX']))
        PRGDataParser(prg_path, all_tags1, 'end', perms_dict, addr_phrs_d, regs_dict)

    # Tworzmy GUI wyswietlajace mape
    # create_gui_window()


if __name__ == "__main__":
    s_time = time.time()
    main()
    logging.getLogger('root').info("Łączny czas wykonywania programu - {:.2f} sekundy.".format(time.time() - s_time))
