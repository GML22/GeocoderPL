""" Module that creates GUI window """

import io
import json
from itertools import cycle

import folium
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWebEngineWidgets import QWebEngineView
from folium.plugins import MousePosition

from db_classes import AddrArr, PRG
from geo_utilities import *


class MyGeoGUI(QtWidgets.QWidget):
    """ Class creating GUI window """

    def __init__(self) -> None:
        super().__init__()
        # Ustalamy patern przeszukiwania
        self.c_ptrn = re.compile(os.environ["RE_PATTERN"])
        self.sekt_num = int(os.environ["SEKT_NUM"])
        self.max_sekts = int(os.environ["MAX_SEKTS"])

        # Pobieramy z bazy danych unikalne ciagi znakow i adressy
        with sa.orm.Session(SQL_ENGINE) as db_session:
            self.addr_uniq_words = db_session.query(UniqPhrs.uniq_phrs).all()[0][0]
            self.addr_arr = pd.read_sql(db_session.query(AddrArr).statement, SQL_ENGINE).to_numpy()

        # Ustalamy najważniejsze parametry okna mapy
        self.setWindowTitle("GeocoderPL")
        icon_path = os.environ["ICON_PATH"]

        try:
            self.setWindowIcon(QIcon(QPixmap(icon_path)))
        except FileNotFoundError:
            raise Exception("Pod podanym adresem: '" + icon_path + "' nie ma pliku 'geo_icon.png'. Uzupełnij ten " +
                            "plik i uruchom program ponownie!")

        self.window_width, self.window_height = 1200, 900
        self.setMinimumSize(self.window_width, self.window_height)
        self.map_layout = QtWidgets.QVBoxLayout()
        self.map_layout.setContentsMargins(0, 0, 0, 0)  # Usuwamy marginesy pomiedzy mapa a oknem
        self.setLayout(self.map_layout)
        self.na_strings = ("", "brak numeru rejestru zabytków", ".")
        self.prev_kol = [0, 1, 2]
        self.inf_names = ["<b>Miejscowość: </b>", "<b>Ulica: </b>", "<b>Numer budynku: </b>", "<b>Kod pocztowy: </b>",
                          "<b>Gmina: </b>", "<b>Powiat: </b>", "<b>Województwo: </b>"]
        self.bubd_names = ["<b>Kategoria budynku: </b>", "<b>Nazwa kartograficzna: </b>", "<b>Stan budynku: </b>",
                           "<b>Funkcja budynku: </b>", "<b>Liczba kondygnacji: </b>", "<b>Zabytek: </b>",
                           "<b>Szacunkowa powierzchnia: </b>"]
        self.res_coords = {}
        self.start_coords = np.asarray((float(os.environ["START_LAT"]), float(os.environ["START_LONG"])))
        self.c_map = folium.Map(title="GEO PYTHON", zoom_start=19, location=self.start_coords, control_scale=True,
                                tiles=None)
        form_lat = "function(num) {return L.Util.formatNum(num, 3) + 'º N';};"
        form_lng = "function(num) {return L.Util.formatNum(num, 3) + 'º E';};"
        self.m_pos = MousePosition(position="topright", separator=" | ", empty_string="NaN", lng_first=False,
                                   num_digits=20, prefix="Bieżące współrzędne: ", lat_formatter=form_lat,
                                   lng_formatter=form_lng)
        self.m_pos.add_to(self.c_map)

        # Dodajemy warstwy do mapy
        self.st_map = folium.TileLayer(tiles='http://tile.stamen.com/toner/{z}/{x}/{y}.png', attr="toner-bcg",
                                       name='Stamen Toner', overlay=True, control=True)
        self.st_map.add_to(self.c_map)
        self.os_map = folium.TileLayer(tiles='OpenStreetMap', name='OpenStreetMap', overlay=True, control=True,
                                       show=False)
        self.os_map.add_to(self.c_map)
        self.gog_map = folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google',
                                        name='Google Satellite', overlay=True, control=True,
                                        show=False)
        self.gog_map.add_to(self.c_map)
        self.c_map.add_child(folium.LayerControl())

        # Dodajemy wyszukiwarke
        ne_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Wyszukiwarka: ")
        label.setStyleSheet("background-color: rgb(255, 255, 255);color: rgb(0, 0, 0); font-size: 25px;" +
                            "font-weight: bold;")
        ne_layout.addWidget(label)
        self.completer = QtWidgets.QCompleter([''])
        self.completer.popup().setStyleSheet("background-color: rgb(255, 255, 255); font-size: 20px;")

        # Ustawiamy completer tak, żeby nie zwracal uwagi na wielkosc liter
        self.completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

        # Ustawiamy completer tak, żeby nie filtrowal wynikow - sami je filtrujemy podajac do completera
        self.completer.setCompletionMode(QtWidgets.QCompleter.UnfilteredPopupCompletion)

        # Wywołujemy funkcje gdy użytkownik wybierze propozycję z autouzupelnienia
        self.completer.activated.connect(self.on_text_selected)

        # Parametryzujemy pole QLineEdit
        self.line_edit = QtWidgets.QLineEdit('')
        self.line_edit.setCompleter(self.completer)
        self.line_edit.setStyleSheet("background-color: rgb(255, 255, 255); font-size: 18px;")
        self.line_edit.setPlaceholderText("Podaj nazwę miejscowości, ulicę, kod pocztowy lub współrzędne geograficzne" +
                                          " (np. 52.21, 21.52)")
        self.line_edit.setClearButtonEnabled(True)

        # Wywołujemy funkcję za każdym razem gdy tekst w oknie qLineEdit zmieni sie tekst
        self.line_edit.textChanged.connect(self.on_text_changed)

        # Wywołujemy funkcję za każdym razem gdy wciśnięty zostanie klawisz "Enter" lub "Return"
        self.line_edit.returnPressed.connect(self.on_text_selected)

        # Parametryzujemy layout
        ne_layout.setContentsMargins(50, 10, 50, 10)
        ne_layout.addWidget(self.line_edit)
        self.map_layout.addLayout(ne_layout)

        # Ustalamy indeksy sektorow zgodnie z algorytmem spirali
        self.c_sekt = get_sector_codes(*self.start_coords)
        self.spiral_ids_arr = np.zeros(((2 * self.sekt_num - 1) ** 2, 2), dtype=np.int16)
        self.prev_val = tuple()
        get_addr_spiral_ids(self.sekt_num, self.spiral_ids_arr)
        c_inds_spiral = self.spiral_ids_arr + self.c_sekt
        c_inds = c_inds_spiral[np.logical_and((c_inds_spiral >= 0).prod(1), (c_inds_spiral < self.sekt_num).prod(1))]

        # Tworzymy listę sektorów posortowaną według odległosci od sektora poczatkowego zgodnie z algorytmem spirali
        self.adds_list = self.addr_arr[c_inds[:, 0], c_inds[:, 1]].flatten()

        # Tworzymy listę ideksów posortwanych sektorów  w 'self.adds_list'
        self.add_sekts = np.indices((self.sekt_num, self.sekt_num)).transpose(1, 2, 0)
        self.sekts_list = self.add_sekts[c_inds[:, 0], c_inds[:, 1]]

        # Dodajemy mape z folium
        data = io.BytesIO()
        self.c_map.save(data, close_file=False)
        web_view = QWebEngineView()
        web_view.setHtml(data.getvalue().decode())
        self.map_layout.addWidget(web_view)

    def on_text_changed(self) -> None:
        """ Method that implements event on text change in QLineEdit """

        # Dodajemy spacje (" ") na początku wyszukiwanej frazy żeby rozróżniać miasta typu: "INNOWROCLAW" i "WROCLAW"
        start_text = self.line_edit.text()
        org_text = " " + start_text
        curr_text = unidecode(org_text.upper()).replace(",", "").replace("UL. ", "")
        last_text = curr_text[max(curr_text.strip().rfind(" ") + 1, 0):].strip()
        self.completer.popup().setStyleSheet("font-size: 20px; font-style: normal; color: black;")
        addrs_num = 5

        if start_text[:14] == "Nie znaleziono":
            self.line_edit.setText("")
            self.completer.model().setStringList([''])
        elif curr_text != "" and ", g" not in org_text and last_text in self.addr_uniq_words:
            ids_row = [''] * addrs_num
            found_flag = False
            sek_licz = 0
            prg_ids = ""

            for i, add in enumerate(self.adds_list):
                if add != "" and curr_text in add and '' in ids_row:
                    found_flag = get_prg_ids(addrs_num, add, curr_text, ids_row)
                elif found_flag and '' in ids_row and sek_licz <= self.max_sekts:
                    sek_licz += 1
                elif '' not in ids_row or (found_flag and sek_licz > self.max_sekts):
                    c_prg = ", ".join(ids_row).strip().replace(" ,", "")
                    c_prg = c_prg[:-1] if c_prg[-1] == ',' else c_prg
                    prg_ids += c_prg
                    self.change_sekts_order(self.sekts_list[i])
                    break

            if prg_ids != "":
                prg_cols = [PRG.miejscowosc, PRG.ulica, PRG.numer, PRG.kod_pocztowy, PRG.gmina, PRG.powiat,
                            PRG.wojewodztwo, PRG.dodatkowy_opis, PRG.szerokosc, PRG.dlugosc, PRG.bdot10_bubd_id]
                prg_cond = sa.or_(PRG.prg_point_id == int(v) for v in prg_ids.split(", "))

                with sa.orm.Session(SQL_ENGINE) as db_session:
                    c_res = pd.read_sql(db_session.query(*prg_cols).filter(prg_cond).statement, SQL_ENGINE).to_numpy()

                res_list = np.array([(", ".join(["ul. " + el if i == 1 else "gmina: " + el if i == 4 else el
                                                 for i, el in enumerate(row) if el not in self.na_strings
                                                 and (i < 5 or i == 7)]), row) for row in c_res], dtype=object)
                self.completer.model().setStringList(res_list[:, 0])
                self.res_coords.update(dict(zip(res_list[:, 0], res_list[:, 1])))
            elif prg_ids == "" and not self.c_ptrn.match(start_text):
                self.completer.model().setStringList(['Wśród adresów z całej Polski nie znaleziono żadnego, który ' +
                                                      'zawierałby frazę: "' + start_text + '"'])
                self.completer.popup().setStyleSheet("font-size: 18px; font-style: italic; color: gray;")
            elif prg_ids == "" and self.c_ptrn.match(start_text):
                self.completer.model().setStringList(['Wciśnij enter, żeby wyszukać punkt adresowy najbliższy podanym' +
                                                      ' współrzędnym'])
                self.completer.popup().setStyleSheet("font-size: 18px; font-style: italic; color: gray;")

        elif last_text not in self.addr_uniq_words and not self.c_ptrn.match(start_text):
            self.completer.model().setStringList(['Wśród adresów z całej Polski nie znaleziono żadnego, który ' +
                                                  'zawierałby frazę: "' + start_text + '"'])
            self.completer.popup().setStyleSheet("font-size: 18px; font-style: italic; color: gray;")
        elif last_text not in self.addr_uniq_words and self.c_ptrn.match(start_text):
            self.completer.model().setStringList(['Wciśnij enter, żeby wyszukać punkt adresowy najbliższy podanym' +
                                                  ' współrzędnym'])
            self.completer.popup().setStyleSheet("font-size: 18px; font-style: italic; color: gray;")

    def change_sekts_order(self, c_sekt: np.ndarray) -> None:
        """ Method that changes order of sectors in adds_list """

        if np.abs(c_sekt - self.c_sekt).max() > self.max_sekts:
            c_ids_spl = self.spiral_ids_arr + c_sekt
            c_inds = c_ids_spl[np.logical_and((c_ids_spl >= 0).prod(1),
                                              (c_ids_spl < self.sekt_num).prod(1))]
            self.adds_list = self.addr_arr[c_inds[:, 0], c_inds[:, 1]].flatten()
            self.sekts_list = self.add_sekts[c_inds[:, 0], c_inds[:, 1]]
            self.c_sekt = c_sekt

    def on_text_selected(self) -> None:
        """ Methond that implements event on text select in QCompleter """

        c_row = list()
        c_text = self.line_edit.text()

        # Ustalamy które dane ze slownika danych adresowych mamy pobrac
        if c_text in self.res_coords:
            c_row = self.res_coords[c_text].tolist()
        # Szukamy po koordynatach
        elif self.c_ptrn.match(c_text):
            # Wybieramy współrzędne
            c_coords = np.asarray(c_text.split(",")).astype(float)

            # Ustalamy sektory dla wybranych wspołrzędnych
            szer, dlug = get_sector_codes(*c_coords)

            # Dla ustalonego sektora dobieramy sektory, ktore go otaczaja, w ten sposob uzyskujac 9 sektorow dla
            # kazdego punktu PRG, z których wybieramy unikalne kombinacje sektorow
            jnd_sekts = [str(max(i, 0)).zfill(3) + "_" + str(min(j, self.sekt_num - 1)).zfill(3)
                         for i in range(szer - 1, szer + 2) for j in range(dlug - 9, dlug + 10)]

            # Pobieramy wszystkie współrzędne dla danego sektora
            prg_cols = [PRG.prg_point_id, PRG.szerokosc, PRG.dlugosc]
            prg_cond = sa.or_(PRG.kod_sektora == v for v in jnd_sekts)

            with sa.orm.Session(SQL_ENGINE) as db_session:
                sekts_coords = pd.read_sql(db_session.query(*prg_cols).filter(prg_cond).statement,
                                           SQL_ENGINE).to_numpy()

            if len(sekts_coords) > 0:
                # Wyliczamy odleglosci euklidesowe
                eukl_dists = np.sqrt((sekts_coords[:, 1] - c_coords[0]) ** 2 + (sekts_coords[:, 2] - c_coords[1]) ** 2)

                # Pobieramy dane dla najbliższego punktu adresowego od podanych przez użytkownika wspołrzędnych
                prg_cols = [PRG.miejscowosc, PRG.ulica, PRG.numer, PRG.kod_pocztowy, PRG.gmina, PRG.powiat,
                            PRG.wojewodztwo, PRG.dodatkowy_opis, PRG.szerokosc, PRG.dlugosc, PRG.bdot10_bubd_id]
                prg_cond = PRG.prg_point_id == int(sekts_coords[eukl_dists.argmin(), 0])

                with sa.orm.Session(SQL_ENGINE) as db_session:
                    c_row = pd.read_sql(db_session.query(*prg_cols).filter(prg_cond).statement,
                                        SQL_ENGINE).to_numpy().tolist()

                self.change_sekts_order(np.asarray([szer, dlug]))
            else:
                self.completer.popup().show()
                self.completer.model().setStringList(['Współrzędne geograficzne poza granicami Polski!'])
                self.completer.popup().setStyleSheet("font-size: 18px; font-style: italic; color: red;")
        else:
            uni_text = unidecode(c_text.replace(",", "")).upper()

            for k, v in self.res_coords.items():
                if uni_text in unidecode(k.replace(",", "")).upper():
                    c_row = v.tolist()
                    self.line_edit.setText(k)
                    break

        if c_row and c_row != self.prev_val:
            self.prev_val = c_row
            info_list = [self.inf_names[i] + el for i, el in enumerate(c_row[:-4]) if el not in self.na_strings]
            c_crds = c_row[-3:-1]
            f_info = ["<font size='4'><b>Dane dotyczące punktu adresowego:</b></font>"] + info_list + \
                     ["<b>Współrzędne: </b>" + str(round(c_crds[0], 3)) + "º N, " + str(round(c_crds[1], 3)) + "º E"]

            # Tworzymy mapę od nowa, żeby polygon był dobrze nakładany na wszystkie mapy
            self.c_map = folium.Map(title="GEO PYTHON", zoom_start=19, location=(c_crds[0] + 0.0007, c_crds[1]),
                                    control_scale=True, tiles=None)

            # Pobieramy kształt budynku dla danego punktu adresowego
            bdot10k_bubd_id = c_row[-1]
            dod_info = ""

            if bdot10k_bubd_id > 0:
                # Pobieramy dane z tabeli budynków
                f_info += ["", "<font size='4'><b>Dane dotyczące budynku:</b></font>"]
                bdot10k_cols = [BDOT10K.kat_budynku, BDOT10K.nazwa_kart, BDOT10K.stan_budynku, BDOT10K.funkcja_budynku,
                                BDOT10K.liczba_kond, BDOT10K.czy_zabytek, BDOT10K.powierzchnia, BDOT10K.opis_budynku,
                                BDOT10K.bubd_geojson]
                bdot10k_cond = BDOT10K.bdot10k_bubd_id == bdot10k_bubd_id

                with sa.orm.Session(SQL_ENGINE) as db_session:
                    bubd_row = pd.read_sql(db_session.query(*bdot10k_cols).filter(bdot10k_cond).statement,
                                           SQL_ENGINE).to_numpy()

                c_geojson = json.loads(bubd_row[-1])
                dod_info = bubd_row[-2]
                f_info += [self.bubd_names[i] + str(int(el)) if i == 4 else
                           self.bubd_names[i] + "Nie" if i == 5 and el == 0 else self.bubd_names[i] + "Tak"
                           if i == 5 and el == 1 else self.bubd_names[i] + str(int(el)) + " m²"
                           if i == 6 else self.bubd_names[i] + str(el) for i, el in enumerate(bubd_row[:-2])
                           if el != ""]

                if dod_info != "":
                    f_info += ["<b>Opis budynku: </b>" + dod_info]

                folium.GeoJson(data=c_geojson, name="Budynek",
                               style_function=lambda x: {'fillColor': 'orange', 'fillOpacity': 0.5,
                                                         'color': 'red'}).add_to(self.c_map)
            else:
                f_info += ["", "<font size='4'><b>Dane dotyczące budynku:</b></font>", "<font color='red'>W bazie " +
                           "BDOT10k nie znajduje się żaden budynek, który byłby", " odddalony o mniej niż 10 metrów," +
                           " od bieżącego punktu adresowego</font>"]

            # Dodajemy finalny marker do mapy
            f_info += ["", "", '<font size="2"><i>Dane pobrane dnia 20. października 2021 roku ze stron ' +
                       'internetowych:<br>' + '<a href="https://dane.gov.pl/pl/dataset/726,panstwowy-rejestr-granic' +
                       '-i-powierzchni-jednostek-podziaow-terytorialnych-kraju/resource/29538/table">https://dane.' +
                       'gov.pl</a><br><a href="https://mapy.geoportal.gov.pl">https://mapy.geoportal.gov.pl</a>' +
                       '</i></font>']
            date_iframe = folium.IFrame("<br>".join(f_info), width=470, height=(len(f_info) + len(dod_info) // 30) * 22)
            date_popup = folium.Popup(date_iframe)
            folium.Marker(location=c_crds, popup=date_popup,
                          icon=folium.Icon(color='red', icon_color='white', icon='globe')).add_to(self.c_map)

            # Dodajemy warstwy do nowoutworzonej mapy
            self.m_pos.add_to(self.c_map)
            self.st_map.add_to(self.c_map)
            self.os_map.add_to(self.c_map)
            self.gog_map.add_to(self.c_map)
            self.c_map.add_child(folium.LayerControl())
            c_data = io.BytesIO()
            self.c_map.save(c_data, close_file=False)
            web_view = QWebEngineView()
            web_view.setHtml(c_data.getvalue().decode())

            # Usuwamy dotychczasowy widget z layoutu
            self.map_layout.itemAt(1).widget().deleteLater()

            # Dodajemy widget z nowymi wspołrzędnymi
            self.map_layout.addWidget(web_view)


def get_addr_spiral_ids(addr_arr_shp: int, spiral_ids_arr: np.ndarray) -> None:
    """ Function that returs indices of numpy array in spiral mode up to 'add_arr' shape starting from central point """

    # Definiujemy podstawowe parametry
    spiral_ids_arr[0, :] = [0, 0]
    add_list = [1, 0]
    c_sign = [1, 1]
    c_kier = cycle([1, 0])
    c_ind = 0
    i = 1
    arr_licz = 1
    c_sum = 0

    while 1:
        # Mnożymy razy 8, bo każdy sektor jest otoczony zawsze 8 sąsiadami
        if arr_licz <= c_sum + 8 * i:
            spiral_ids_arr[arr_licz, :] = add_list
            arr_licz += 1
        else:
            c_sum += 8 * i
            i += 1

            if i == addr_arr_shp:
                return

            add_list = list(spiral_ids_arr[arr_licz - 1, :])
            add_list[0] += 1
            spiral_ids_arr[arr_licz, :] = add_list
            arr_licz += 1

        if add_list[c_ind] >= i or add_list[c_ind] <= -i:
            c_ind = next(c_kier)

            if add_list[c_ind] >= i or add_list[c_ind] <= -i:
                c_sign[c_ind] *= -1

        add_list[c_ind] += c_sign[c_ind]


def get_prg_ids(prg_num: int, c_addrs: str, curr_text: str, ids_row: list) -> bool:
    """ Function that generates indices of points in PRG table matching current text """

    # Definiujemy podstawowe parametry
    c_start = 0
    found_flag = False
    empty_idx = ids_row.index('')

    for i in range(prg_num):
        if '' not in ids_row:
            break

        str_idx1 = c_addrs.find(curr_text, c_start)

        if str_idx1 >= 0:
            str_idx2 = c_addrs.find(' [', str_idx1) + 2
            str_idx3 = c_addrs.find(']', str_idx2)
            ids_row[empty_idx + i] = c_addrs[str_idx2:str_idx3]
            c_start = str_idx3
            found_flag = True

    return found_flag
