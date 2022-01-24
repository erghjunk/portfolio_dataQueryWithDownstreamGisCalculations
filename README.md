# Python Portfolio - Data compilation based on river flow direction and distance

This script compiles environmental justice metrics (published by US EPA) within one mile (downstream) of wastewater treatment facilities. It uses the ArcPy (ESRI) API. 

author: evan fedorko, evanjfedorko@gmail.com
date: 12/2019
last check: 1/2022; runs with ArcGIS Desktop 10.8.1 and whichever
antiquated version of Python (2.7 probably) that installs with that software.
also requires pandas. This script will run if you download the (very very) 
simple test data and put everything in one directory.

the client wanted to compile environmental justice information
(as published by the EPA) for water discharging facilities in the US,
and specifically, for people living within 1 mile downstream of the discharge
this script is the ULTRA budget version of that analysis. At the time of writing
the published tools for doing this sort of analysis with NHDPlus data did not
work, or required some major hoops, so I wrote this instead. A lot of the "power"
of this analysis is wrapped up in the power of the NHD data itself.

the major weaknesses of this analysis (concessions to time/budget) are:

1. actual discharge distance is, essentially, approximated
2. EJ polygons are at a very different scale than drainage
polygons and this is entirely unaccounted for; if an EJ
polygon intersects a drainage polygon, all it's data are included
for that facility

most of this is solveable with, you guessed it, more time.
