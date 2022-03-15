""" __init_.py modelue """
import os
import sqlite3
import time
import logging

from gather_bdot10k_data import create_bdot10k_table
from gather_prg_data import create_prg_table
from generate_regs_dicts import create_regs_dicts
from geo_gui import create_gui_window
from geo_utilities import time_decorator, create_logger

# Tworzymy domyślny obiekt loggera
create_logger('root')


@time_decorator
def main():
    """ Main function """

    # Definicja nazwy bazy danych
    db_name = 'PRG_BDOT10K_database.db'

    # Oczekiwana precyzja koordynatow
    coords_prec = 6

    # Liczba sektorow przestrzennych, na ktore maja byc podzielone punkty PRG
    sekt_num = 200

    # Maksymalna odleglosc (w metrach) punktu adresowego PRG od budynku BDOT10k, która kwalifikuje dany budynek jako
    # przypisany danemu punktowi adresowemu
    max_dist = 10

    # Deklaracja najwazniejszych sciezek
    curr_dir = os.getcwd()
    parent_path = os.path.abspath(os.path.join(os.path.join(curr_dir, os.pardir), os.pardir))
    fls_path = os.path.join(parent_path, "files\\")
    lyrs_path = os.path.join(parent_path, "layers\\")

    # Definiujemy sciezke do bazy danych
    db_path = os.path.join(fls_path, db_name)

    # Tworzymy słownik kształtów
    regs_dict = create_regs_dicts(fls_path, lyrs_path)

    # Laczymy sie z baza danych 'PRG_BDOT10K_database.db'
    curr_conn = sqlite3.connect(db_path)
    cursor = curr_conn.cursor()

    # Sprawdzamy w bazie czy istnieje tablica BDOT10K_TABLE, jezeli istnieje to idziemy dalej jezeli nie to ja tworzymy
    cursor.execute("SELECT * FROM sqlite_master WHERE name ='BDOT10K_TABLE' and type='table'")
    bdot10k_res = cursor.fetchone()

    if bdot10k_res is None:
        # Wczytujemy informacje o budynkach BUBD BDOT10K do bazy SQL
        create_bdot10k_table(fls_path, lyrs_path, coords_prec, curr_conn, cursor, sekt_num)

    # Sprawdzamy w bazie czy istnieje tablica PRG_TABLE, jezeli istnieje to idziemy dalej jezeli nie to ja tworzymy
    cursor.execute("SELECT * FROM sqlite_master WHERE name='PRG_TABLE' and type='table'")
    prg_res = cursor.fetchone()

    if prg_res is None:
        # Tworzymy bazę SQL z punktami adresowymi PRG i sprawdzamy poprawnosc wspolrzednych tych punktow
        create_prg_table(lyrs_path, fls_path, regs_dict, curr_conn, cursor, coords_prec, sekt_num, max_dist)

    # Tworzmy GUI wyswietlajace mape
    create_gui_window(fls_path, cursor, sekt_num)

    # Zamkniecie polaczenia z baza
    cursor.close()


if __name__ == "__main__":
    strt_time = time.time()
    main()
    logging.getLogger('root').info("Łączny czas wykonywania programu - {:.2f} sekundy.".format(time.time() - strt_time))
