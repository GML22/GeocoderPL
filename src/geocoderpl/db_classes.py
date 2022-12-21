""" Module that defines SQL database classes """

import os

import sqlalchemy as sa
from dotenv import load_dotenv
from sqlalchemy.orm import declarative_base

# Tworzymy bazowy schemat dla tabel
BASE = declarative_base()

# Wczytujemy zmienne środowiskowe projektu
parent_path = os.path.join(os.getcwd()[:os.getcwd().index("GeocoderPL")], "GeocoderPL")
load_dotenv(os.path.join(parent_path, ".env"))
os.environ["PARENT_PATH"] = parent_path

# Deklarujemy silnik SQL
SQL_ENGINE = sa.create_engine("sqlite:///" + os.path.join(os.environ["PARENT_PATH"], os.environ["DB_PATH"]))


class BDOT10K(BASE):
    """ Class that defines columns of 'BDOT10K_TABLE' """

    # Defniujemy nazwę tabeli
    __tablename__ = "BDOT10K_TABLE"

    # Definiujemy kolumny tabeli
    bdot10k_bubd_id = sa.Column('BDOT10K_BUBD_ID', sa.Integer, primary_key=True)
    kod_sektora = sa.Column('KOD_SEKTORA', sa.String, nullable=False, index=True)
    kat_budynku = sa.Column('KATEGORIA_BUDYNKU', sa.String, nullable=False)
    nazwa_kart = sa.Column('NAZWA_KARTOGRAFICZNA', sa.String, nullable=False)
    stan_budynku = sa.Column('STAN_BUDYNKU', sa.String, nullable=False)
    funkcja_budynku = sa.Column('FUNKCJA_BUDYNKU', sa.String, nullable=False)
    liczba_kond = sa.Column('LICZBA_KONDYGNACJI', sa.Float, nullable=False)
    czy_zabytek = sa.Column('CZY_ZABYTEK', sa.Integer, nullable=False)
    opis_budynku = sa.Column('OPIS_BUDYNKU', sa.String, nullable=False)
    powierzchnia = sa.Column('POWIERZCHNIA', sa.Float, nullable=False)
    centr_lat = sa.Column('CENTROID_LAT', sa.Float, nullable=False)
    centr_long = sa.Column('CENTROID_LONG', sa.Float, nullable=False)
    bubd_geojson = sa.Column('BUBD_GEOJSON', sa.Text, nullable=False)

    # Definiujemy połaczenie do klasy PRG
    children = sa.orm.relationship("PRG")

    def __init__(self, kod_sektora: str, kat_budynku: str, nazwa_kart: str, stan_budynku: str, funkcja_budynku: str,
                 liczba_kond: float, czy_zabytek: int, opis_budynku: str, powierzchnia: float, centr_lat: float,
                 centr_long: float, bubd_geojson: str) -> None:
        self.kod_sektora = kod_sektora
        self.kat_budynku = kat_budynku
        self.nazwa_kart = nazwa_kart
        self.stan_budynku = stan_budynku
        self.funkcja_budynku = funkcja_budynku
        self.liczba_kond = liczba_kond
        self.czy_zabytek = czy_zabytek
        self.opis_budynku = opis_budynku
        self.powierzchnia = powierzchnia
        self.centr_lat = centr_lat
        self.centr_long = centr_long
        self.bubd_geojson = bubd_geojson

    def __repr__(self) -> str:
        return "<BDOT10K('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')>" % \
               (self.kod_sektora, self.kat_budynku, self.nazwa_kart, self.stan_budynku, self.funkcja_budynku,
                self.liczba_kond, self.czy_zabytek, self.opis_budynku, self.powierzchnia, self.centr_lat,
                self.centr_long, self.bubd_geojson)


class PRG(BASE):
    """ Class that defines columns of 'PRG_TABLE' """

    # Defniujemy nazwę tabeli
    __tablename__ = "PRG_TABLE"

    # Definiujemy kolumny tabeli
    prg_point_id = sa.Column('PRG_POINT_ID', sa.Integer, primary_key=True)
    wojewodztwo = sa.Column('WOJEWODZTWO', sa.String, nullable=False)
    powiat = sa.Column('POWIAT', sa.String, nullable=False)
    gmina = sa.Column('GMINA', sa.String, nullable=False)
    miejscowosc = sa.Column('MIEJSCOWOSC', sa.String, nullable=False)
    miejscowosc2 = sa.Column('MIEJSCOWOSC2', sa.String, nullable=False)
    ulica = sa.Column('ULICA', sa.String, nullable=False)
    numer = sa.Column('NUMER', sa.String, nullable=False)
    kod_pocztowy = sa.Column('KOD_POCZTOWY', sa.String, nullable=False)
    status = sa.Column('STATUS', sa.String, nullable=False)
    szerokosc = sa.Column('SZEROKOSC', sa.Float, nullable=False)
    dlugosc = sa.Column('DLUGOSC', sa.Float, nullable=False)
    zrodlo = sa.Column('ZRODLO', sa.String, nullable=False)
    czy_poprawny = sa.Column('CZY_POPRAWNY', sa.Integer, nullable=False)
    odleglosc_od_gminy = sa.Column('ODLEGLOSC_OD_GMINY', sa.Float, nullable=False)
    bdot10_bubd_id = sa.Column('BDOT10K_BUBD_ID', sa.Integer, sa.ForeignKey('BDOT10K_TABLE.BDOT10K_BUBD_ID'),
                               nullable=False)
    odleglosc_od_budynku = sa.Column('ODLEGLOSC_OD_BUDYNKU', sa.Float, nullable=False)
    kod_sektora = sa.Column('KOD_SEKTORA', sa.String, nullable=False, index=True)
    dodatkowy_opis = sa.Column('DODATKOWY_OPIS', sa.String, nullable=False)

    def __init__(self, wojewodztwo: str, powiat: str, gmina: str, miejscowosc: str, miejscowosc2: str, ulica: str,
                 numer: str, kod_pocztowy: str, status: str, szerokosc: float, dlugosc: float, zrodlo: str,
                 czy_poprawny: int, odleglosc_od_gminy: float, bdot10_bubd_id: int, odleglosc_od_budynku: float,
                 kod_sektora: str, dodatkowy_opis: str) -> None:
        self.wojewodztwo = wojewodztwo
        self.powiat = powiat
        self.gmina = gmina
        self.miejscowosc = miejscowosc
        self.miejscowosc2 = miejscowosc2
        self.ulica = ulica
        self.numer = numer
        self.kod_pocztowy = kod_pocztowy
        self.status = status
        self.szerokosc = szerokosc
        self.dlugosc = dlugosc
        self.zrodlo = zrodlo
        self.czy_poprawny = czy_poprawny
        self.odleglosc_od_gminy = odleglosc_od_gminy
        self.bdot10_bubd_id = bdot10_bubd_id
        self.odleglosc_od_budynku = odleglosc_od_budynku
        self.kod_sektora = kod_sektora
        self.dodatkowy_opis = dodatkowy_opis

    def __repr__(self) -> str:
        print_str = "<PRG('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s'," + \
                    " '%s', '%s', '%s')>"
        return print_str % (self.wojewodztwo, self.powiat, self.gmina, self.miejscowosc, self.miejscowosc2, self.ulica,
                            self.numer, self.kod_pocztowy, self.status, self.szerokosc, self.dlugosc, self.zrodlo,
                            self.czy_poprawny, self.odleglosc_od_gminy, self.bdot10_bubd_id, self.odleglosc_od_budynku,
                            self.kod_sektora, self.dodatkowy_opis)


class UniqPhrs(BASE):
    """ Class that defines unique phrases """

    # Defniujemy nazwę tabeli
    __tablename__ = 'UNIQ_TABLE'

    # Definiujemy kolumny tabeli
    uniq_id = sa.Column('UNIQ_ID', sa.Integer, primary_key=True)
    uniq_phrs = sa.Column('UNIQ_PHRS', sa.Text, primary_key=False)

    def __init__(self, uniq_phrs: str) -> None:
        self.uniq_phrs = uniq_phrs

    def __repr__(self) -> str:
        return "<UniqPhrs('%s')>" % self.uniq_phrs


class TerytCodes(BASE):
    """ Class that defines TERYT codes """

    # Defniujemy nazwę tabeli
    __tablename__ = 'TERYT_TABLE'

    # Definiujemy kolumny tabeli
    teryt_id = sa.Column('TERYT_ID', sa.Integer, primary_key=True)
    teryt_name = sa.Column('TERYT_NAME', sa.String, primary_key=False)
    teryt_code = sa.Column('TERYT_CODE', sa.String, primary_key=False)

    def __init__(self, teryt_name: str, teryt_code: str) -> None:
        self.teryt_name = teryt_name
        self.teryt_code = teryt_code

    def __repr__(self) -> str:
        return "<TerytCodes('%s', '%s')>" % (self.teryt_name, self.teryt_code)


class RegJSON(BASE):
    """ Class that defines regional JSON files """

    # Defniujemy nazwę tabeli
    __tablename__ = 'JSON_TABLE'

    # Definiujemy kolumny tabeli
    json_id = sa.Column('JSON_ID', sa.Integer, primary_key=True)
    json_name = sa.Column('JSON_NAME', sa.String, primary_key=False)
    json_teryt = sa.Column('JSON_TERYT', sa.String, primary_key=False)
    json_shape = sa.Column('JSON_SHAPE', sa.Text, primary_key=False)

    def __init__(self, json_name: str, json_teryt: str, json_shape: str) -> None:
        self.json_name = json_name
        self.json_teryt = json_teryt
        self.json_shape = json_shape

    def __repr__(self) -> str:
        return "<RegJSON('%s', '%s', '%s')>" % (self.json_name, self.json_teryt, self.json_shape)
