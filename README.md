# GeocoderPL
<p align="justify">
GeocoderPL is an application written in Python, which can be used for geocoding address points in Poland along with the possibility to display basic information about a given address point and the building assigned to this address. </p>

<p align="center">
  <img width=75% height=75% src="/imgs/GeocoderPL.png"/>
</p>

<p align="justify">
GeocoderPL uses two main data sorces: <br>
  1. The National Register of Boundaries (PRG) - state maintained reference database of all address points in Poland (including administrative division of the country): https://dane.gov.pl/pl/dataset/726,panstwowy-rejestr-granic-i-powierzchni-jednostek-podziaow-terytorialnych-kraju/resource/29538 <br>
  2. The Topographic Objects Database (BDOT10k) -  state maintained vector database which contains the spatial location of all topographic features in Poland: https://opendata.geoportal.gov.pl/bdot10k/Polska_GML.zip </p>
  
<p align="justify">
Data contained in the abovementioned databases are parsed from GML format to SQLite database. Every address point is validated by checking if its spatial coordinates lie inside shapefile of its district
</p>
