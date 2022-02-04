# HAC ENC Excel Transformer

This repository is for my pet project in Python which takes Excel workbook
produced by HAC (Croatian Motorways, operator of tolled roads in Croatia)
parses it and calculates distances and speeds it took to pass from registered
entry to exit point for each record. 

Results are then written into JSON file for easier consumption in apps, e.g.
the one that could show the heatmap of your movement, and into new Excel
workbook for easier viewing since it is human-readable.

Standard disclaimers of fitness for purpose, liabilities and such apply.

Road distance calculation makes use of the fantastic TomTom routing API, 
which is free for occasional developer usage with registraton on their 
website https://developer.tomtom.com/ 

This project is in early stage of development, developed in my spare time.
It contains my both my own programming code and code fragments gathered 
from public domain and of unknown origin. MIT-style license seems to be the
best choice here. Anyone is welcome to join and contribute, clone and make
derivate work out of it.

This project makes use of both standard library and PyPI modules.

On my wish list for this project is to convert it into 'venv' structure, 
and along side with CLI also provide a REST API micro-service that could
be consumed from a web-UI or a mobile app.
