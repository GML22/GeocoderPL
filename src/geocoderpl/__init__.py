""" __init_.py module """
import logging
import os
import time

import sqlalchemy as sa
from dotenv import load_dotenv

from gather_bdot10k_data import create_bdot10k_table
from gather_prg_data import create_prg_table
from generate_regs_dicts import create_regs_dicts
from geo_gui import create_gui_window
from geo_utilities import time_decorator, create_logger

# Tworzymy domyślny obiekt loggera
create_logger('root')

# Wczytujemy zmienne środowiskowe projektu
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
os.environ["PARENT_PATH"] = os.path.abspath(os.path.join(os.path.join(os.getcwd(), os.pardir), os.pardir))


@time_decorator
def main() -> None:
    """ Main function """

    # Tworzymy słownik kształtów
    regs_dict = create_regs_dicts()

    # Tworzymy silnik do bazy danych 'PRG_BDOT10K_database.db'
    dp_path = os.path.join(os.environ["PARENT_PATH"], os.environ["DB_PATH"])
    sql_engine = sa.create_engine("sqlite:///" + dp_path, echo=False, future=True)
    insp = sa.inspect(sql_engine)

    # Sprawdzamy w bazie czy istnieje tablica 'BDOT10K_TABLE'
    if not insp.has_table('BDOT10K_TABLE'):
        # Tworzymy tabelę 'BDOT10K_TABLE' z danymi o budynkach
        create_bdot10k_table(sql_engine)

    # Sprawdzamy w bazie czy istnieje tablica 'PRG_TABLE'
    if not insp.has_table('PRG_TABLE'):
        # Tworzymy tabelę SQL z punktami adresowymi PRG i sprawdzamy poprawnosc wspolrzednych tych punktow
        create_prg_table(regs_dict)

    # Tworzmy GUI wyswietlajace mape
    create_gui_window(fls_path, cursor, sekt_num, start_lat, start_long, max_sekts)

    # Zamkniecie polaczenia z baza
    cursor.close()


if __name__ == "__main__":
    s_time = time.time()
    main()
    logging.getLogger('root').info("Łączny czas wykonywania programu - {:.2f} sekundy.".format(time.time() - s_time))
