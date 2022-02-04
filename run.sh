#!/bin/bash

# your TomTom Api Auth Key here
export TOMTOM_AUTH_KEY=

HAC_ENC_INPUT_EXCEL="HAC_ENC_Sve_transakcije.xlsx"

export DEBUG=1

./hacTollSpeed.py -g autocesta_ulazi_izlazi.csv \
  -l "HAC_ENC_transform.log" \
  -x "HAC_ENC_Sve_transakcije.plusBrzina.xlsx" \
  -j "HAC_ENC_Sve_transakcije.plusBrzina.json" \
  "${HAC_ENC_INPUT_EXCEL}"
  
