#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# @author Copyright (c) 2022 Damir Dzeko Antic
# @version 0.1.1
# @lastUpdate 2022-02-02

# ChangeLog:
# - can be tested with: python3 -m unittest hacGpsPoints.py


import sys
try:
    assert (sys.version_info.major == 3 and sys.version_info.minor >= 7), "Python version must be 3.7 or newer"
except Exception as e:
    print (e)
    sys.exit(1)

from os import environ
import re
import csv
import unittest

# enumeration for columnar formats we know how to deal with

class CSV_Dialect_local(csv.Dialect):
    delimiter      = ';'
    doublequote    = True
    quotechar      = '"'
    lineterminator = '\n'
    quoting        = csv.QUOTE_ALL

csv.register_dialect('local', CSV_Dialect_local)

# check if debugging requested via environment variable DEBUG
try:
    DEBUG = int(environ.get('DEBUG'))
except:
    DEBUG = 0


class Dict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class HAC_gpsPoints(dict):
    """
    is this class a singleton or it just deviates from the usual object-oriented design
    anyway, do not attempt to create multiple instances
    """
    hac_gpsPoints = dict()

    # called to check if key exists in registry
    @classmethod
    def lookup(classObj, mjesto):
        return classObj.hac_gpsPoints[mjesto] if mjesto in classObj.hac_gpsPoints else None

    @classmethod
    def loadFromCsvFile(classObj, fn):
        """ read in the GPS points of entries and exits to Croatian Highways (HAC) road network
        """
        fn_match = re.match('(?i)^.*\.csv$', fn)
        if not fn_match:
            raise HAC_gpsPoints_Error(f'Not our file name: "{fn}"')

        with open(fn, 'r', encoding='utf-8', newline=None) as file:
            _1st_line = file.readline().rstrip('\n')
            if _1st_line == r'"Naplatna postaja HAC";"GPS pin ulaza";"GPS pin izlaza"':
                dialect = csv.get_dialect('local')
                has_header = True
            else:
                raise HAC_gpsPoints_Error(f'Format of the file "{fn}" not recognized:\n  {repr(_1st_line)}')
            
            file.seek(0)  # Rewind.
            reader = csv.reader(file, dialect)

            if has_header:
                next(reader)  # Skip header row.
            
            for row in reader:
                try:
                    mjesto,gps_ulaz,gps_izlaz,*tail = row
                except Exception as e:
                    raise HAC_gpsPoints_Error(f'In line {reader.line_num}, something strange: {row}\n  {str(e)}')
                
                if len(mjesto) == 0 or mjesto.startswith('#'):  # row commented out
                    continue

                hac_topo = HAC_gpsPoints(mjesto)

                if gps_ulaz:
                    hac_topo.setPoint('ulaz', *re.split(', ?', gps_ulaz))

                if gps_izlaz:
                    hac_topo.setPoint('izlaz', *re.split(', ?', gps_izlaz))


    # called to create an object and register it
    def __init__(self, mjesto):
        dict.__init__(self)
        self._key = mjesto
        HAC_gpsPoints.hac_gpsPoints[self._key] = self

    # called to create a named point coordinates
    def setPoint(self, pointName, lon, lat):
        self[pointName] = Dict({'lon': format(float(lon), '.6f'), 'lat': format(float(lat), '.6f')})

    def getPoint(self, pointName):
        return [ self[pointName].lon, self[pointName].lat ] if pointName in self else None



class HAC_gpsPoints_Error(Exception):
    """Exception raised for errors while loading GPS Points.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message=f'Failed to load GPS Points at "{{__name__}}"'):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}'


class TestHacGpsPoints(unittest.TestCase):
    def setUp(self):
        self.hac_gpsPoints = HAC_gpsPoints.loadFromCsvFile('autocesta_ulazi_izlazi.csv')

    def test_hac_gps_point_1(self):
        actual = HAC_gpsPoints.lookup('Otočac')
        expected = {"ulaz": {"lon": "44.891475", "lat": "15.190142"}, "izlaz": {"lon": "44.892615", "lat": "15.188661"}}
        self.assertEqual(actual, expected)

    def test_hac_gps_point_2(self):
        actual = HAC_gpsPoints.lookup('Dugobabe') # 'Vučevica' would actually work (on the full HAC data set)
        expected = None
        self.assertEqual(actual, expected)

def main():
    raise HAC_gpsPoints_Error(f'{__file__} should not be run as stand-alone program')

if __name__ == '__main__':
    sys.exit(main())

