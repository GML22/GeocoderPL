# GeocoderPL

*[This project was completed in April 2023]*

<p align="justify">
GeocoderPL is an application written in Python, which can be used for geocoding address points in Poland along with the possibility to display basic information about a given address point and the building assigned to this address. GeocoderPL has a form of search engine with three map layers: OpenStreetMap, Google Maps and Stamens Map.</p>

<p align="center">
  <img width=75% height=75% src="/imgs/GeocoderPL.gif"/>
</p>

<p align="justify">
GeocoderPL creates SQL database containing all address points and buildings in Poland by parsing files in Geography Markup Language format to SQL tables. The main data sources of GeocoderPL are following:<br>

  1. The National Register of Boundaries Database (a.k.a. PRG database)- state maintained reference database of all address points in Poland (including administrative division of the country):<br>
  https://dane.gov.pl/pl/dataset/726,panstwowy-rejestr-granic-i-powierzchni-jednostek-podziaow-terytorialnych-kraju/resource/29538 <br>
  https://dane.gov.pl/pl/dataset/726,panstwowy-rejestr-granic-i-powierzchni-jednostek-podziaow-terytorialnych-kraju/resource/29515 <br>
  
  2. The Topographic Objects Database (a.k.a. BDOT10k database) -  state maintained vector database which contains the spatial location of all topographic features in Poland:<br> https://opendata.geoportal.gov.pl/bdot10k/Polska_GML.zip 

The SQL database created in this way can easily cooperate with GeocoderPL search engine - when the user type the name of the city, street or postal code, query to SQL database is sent. 
</p>
  
<p align="center">
  <img width=75% height=75% src="/imgs/GeocoderPL_KR.png"/>
</p>
  
<p align="justify">
Geographic coordinates of every address point from the PRG database are cross-validated by checking that they lie inside the polygon of their district. For every address point in PRG database the closest building in the BDOT10k database is found and if the distance between polygon of this building and address point is less than 10 meters then the building is assigned to adress point.
</p>

<p align="center">
  <img width=75% height=75% src="/imgs/GeocoderPL_WR.png"/>
</p>

<p align="center">
  <img width=75% height=75% src="/imgs/GeocoderPL_GD.png"/>
</p>

<p align="justify">
Geocoding using GeocoderPL search engine requires providing city name, street, building number or postal code of the address point for which we would like to find geographic coordinates. It is also possible to perform reverse geocoding - if you pass geographic coordinates to search engine then you will receive address point closest to these coordinates.
</p>

<p align="center">
  <img width=75% height=75% src="/imgs/GeocoderPL_RG.png"/>
</p>

<p align="center">
  <img width=75% height=75% src="/imgs/GeocoderPL_POZ.png"/>
</p>

<p align="justify">
GeocoderPL can be also used for finding address point by providing name of public institution, church or shop - for part of builings such information is avaible in BDOT10k database, so they are also present in GeocoderPL search engine. GeocoderPL search engine does not utilize any external search engines - it relies only on data gather in SQL database fed with Polish government data and on three map layers: OpenStreetMap, Google Maps and Stamen's Map (visualisation purpose only).
</p>

<p align="center">
  <img width=75% height=75% src="/imgs/GeocoderPL_BK.png"/>
</p>

<p align="left">
The technical documentation of GeocoderPL is available at:
  
- https://gml22.github.io/GeocoderPL
- https://gml22.github.io/GeocoderPL/GeocoderPL%20-%20technical%20documentation.pdf
</p>
