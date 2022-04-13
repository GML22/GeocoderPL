""" __init_.py module """

from PyQt5 import QtWidgets

from db_classes import BASE
from geo_gui import MyGeoGUI
from geo_utilities import *
from xml_parsers import BDOT10kDataParser, PRGDataParser

# Tworzymy domyślny obiekt loggera
create_logger('root')


@time_decorator
def main() -> None:
    """ Main function """

    # Sprawdzamy w bazie czy tablica 'BDOT10K_TABLE' istnieje
    if not sa.inspect(SQL_ENGINE).has_table("BDOT10K_TABLE"):
        # Tworzymy domyslne obiekty tabel BDOT10K i PRG
        BASE.metadata.create_all(SQL_ENGINE)

        # Tworzymy tabele z macierza addresow oraz unikalnych fraz
        with sa.orm.Session(SQL_ENGINE) as db_session:
            db_session.add(UniqPhrs(''))
            db_session.commit()

        # Wypełniamy tablice zwiazane z parametrami regionow
        fill_regs_tables()

        # Tworzymy tabelę 'BDOT10K_TABLE' z danymi o budynkach
        m_tags = os.environ['BDOT10K_TAGS'].split(";")
        all_tags = (m_tags[0], m_tags[1], m_tags[2], m_tags[3], m_tags[4], m_tags[5], m_tags[6], m_tags[7])
        dicts_tags = {m_tags[0]: m_tags[-4], m_tags[1]: m_tags[-3], m_tags[2]: m_tags[-2], m_tags[3]: m_tags[-1]}
        tags_dict = {tag: i for i, tag in enumerate(all_tags)}
        bdot10k_path = os.path.join(os.environ["PARENT_PATH"], os.environ['BDOT10K_PATH'])
        BDOT10kDataParser(bdot10k_path, all_tags, 'end', dicts_tags, tags_dict)

        # Tworzymy tabelę SQL z punktami adresowymi PRG
        prg_path = os.path.join(os.environ["PARENT_PATH"], os.environ['PRG_PATH'])
        all_tags1 = tuple(os.environ['PRG_TAGS'].split(";"))
        perms_dict = get_super_permut_dict(int(os.environ['SUPPERM_MAX']))
        PRGDataParser(prg_path, all_tags1, 'end', perms_dict)

    # Tworzmy GUI wyswietlajace mape
    geo_app = QtWidgets.QApplication(sys.argv)
    geo_app.setStyleSheet('''QWidget {background-color: rgb(255, 255, 255);}''')
    my_geo_gui = MyGeoGUI()
    my_geo_gui.show()

    try:
        sys.exit(geo_app.exec_())
    except SystemExit:
        raise Exception("Przy zamykaniu okna aplikacji wystąpił błąd!")


if __name__ == "__main__":
    s_time = time.time()
    main()
    logging.getLogger('root').info("Łączny czas wykonywania programu - {:.2f} sekundy.".format(time.time() - s_time))
