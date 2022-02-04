#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# @author Copyright (c) 2022 Damir Dzeko Antic
# @version 0.1.0
# @lastUpdate 2022-02-02

import sys
try:
    assert (sys.version_info.major == 3 and sys.version_info.minor >= 7), "Python version must be 3.7 or newer"
except Exception as e:
    print (e)
    sys.exit(1)

import time
from datetime import timedelta

from requests_cache import CachedSession
import unittest
import json

class TomTomLookup():

    def _make_throttle_hook(timeout=1.0):
        """Make a request hook function that adds a custom delay for non-cached requests"""
        def hook(response, *args, **kwargs):
            if not getattr(response, 'from_cache', False):
                # print('sleeping')
                time.sleep(timeout)
            return response
        return hook

    def __init__(self):
        session = CachedSession('./requests_cache.db', 
            backend='sqlite', 
            timeout=30, 
            expire_after=timedelta(days=30),
            old_data_on_error=True,
            serializer='json')
        session.hooks['response'].append(TomTomLookup._make_throttle_hook(1.25))
        self.session = session

    def getUrl(self, url):
        response = self.session.get(url)
        if response.status_code != 200:
            raise Exception("TomTomLookup: GET call returned invalid response")
        return response.text

    def getDistance(self, url):
        response_text = self.getUrl(url)
        try:
            json_obj = json.loads(response_text)
            return json_obj['routes'][0]['summary']['lengthInMeters']
        except:
            raise Exception("TomTomLookup: Failed to decode REST API response")


class TestTomTomLookup(unittest.TestCase):
    def setUp(self):
        self.tomtom = TomTomLookup()

    def test_one_url(self):
        response_text = self.tomtom.getUrl('http://httpbin.org/delay/4')
        response_obj = json.loads(response_text)
        self.assertTrue(response_obj['url'] is not None)


def main():
    print(f'{__file__} should not be run as stand-alone program')
    return 2

if __name__ == '__main__':
    sys.exit(main())