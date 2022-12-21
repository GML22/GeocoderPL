""" GeocoderPL setup file """

import setuptools

setuptools.setup(
    name='geocoderpl',
    version='1.1',
    description='GeocoderPL is an application written in Python, which can be used for geocoding address points in ' +
                'Poland along with the possibility to display basic information about a given address point and the ' +
                'building assigned to this address. GeocoderPL has a form of search engine with three map layers: ' +
                'OpenStreetMap, Google Maps and Stamens Map.',
    author='Mateusz Gomulski',
    author_email='mateusz.gomulski@gmail.com',
    license="MIT License",
    keywords="search-engine geocoding numpy pyqt5 geospatial sqlite3 gdal-python superpermutation folium-maps",
    url="https://github.com/GML22/GeocoderPL",
    python_requires='>=3.8',
    packages=setuptools.find_packages(include=['geocoderpl']),
    install_requires=['folium~=0.12.1',
                      'numpy~=1.20.1',
                      'pyqt5~=5.15.6',
                      'unidecode~=1.3.2',
                      'pyproj~=3.2.1',
                      'lxml~=4.6.3',
                      'geocoder~=1.38.1',
                      'pandas~=1.2.4',
                      'matplotlib~=3.5.0',
                      'setuptools>=52.0.0',
                      'sqlalchemy>=1.4.7',
                      'python-dotenv>=0.19.2]']
)
