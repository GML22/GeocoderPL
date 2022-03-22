import sqlalchemy as sa

# Tworzymy bazowych schemat dla tabel
Base = sa.orm.declarative_base()


class BDOT10K(Base):
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
    bubd_geojson = sa.Column('BUBD_GEOJSON', sa.String, nullable=False)

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


class PRG(Base):
    """ Class that defines columns of 'BDOT10K_TABLE' """

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
        return "<PRG('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')>" % \
               (self.wojewodztwo, self.powiat, self.gmina, self.miejscowosc, self.miejscowosc2, self.ulica, self.numer,
                self.kod_pocztowy, self.status, self.szerokosc, self.dlugosc, self.zrodlo, self.czy_poprawny,
                self.odleglosc_od_gminy, self.bdot10_bubd_id, self.odleglosc_od_budynku, self.kod_sektora,
                self.dodatkowy_opis)
