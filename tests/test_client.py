# -*- coding: utf-8 -*-
import sys
PY26 = sys.version_info[0] == 2 and sys.version_info[1] == 6

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s %(levelname)s %(message)s',
)

import json

if PY26:
    import unittest2 as unittest

else:
    import unittest

import requests

from httmock import all_requests, HTTMock

from checkmyws import CheckmywsClient
from checkmyws import CheckmywsError

client = None
check_id = "3887e18a-28d6-4eac-9eb0-c6d9075e4c7e"

@all_requests
def mock_200(url, request):
    return {'status_code': 200, 'content': None}

@all_requests
def mock_200_json(url, request):
    return {'status_code': 200, 'content': {'_id': '_id'}}

@all_requests
def mock_404(url, request):
    return {'status_code': 404, 'content': None}


@all_requests
def mock_401(url, request):
    return {'status_code': 401, 'content': None}


@all_requests
def mock_status(url, request):
    status = {
        "_id": check_id,
        "laststatechange_bin": 1392506884,
        "metas": {
            "title": "Check my Website",
        },
        "state": 0,
        "states": {
            "ES:MAD:OVH:DC": 0,
            "US:NY:DGO:DC": 0
        },
        "url": "http://www.checkmy.ws"
    }
    return {'status_code': 200, 'content': status}


class TestCase(unittest.TestCase):

    def test_01_init(self):
        global client
        client = CheckmywsClient()

    def test_02_request(self):
        with HTTMock(mock_200):
            client.request("/one/path", method="GET", status_code=200)

        with HTTMock(mock_200):
            client.request("/one/path", method="POST", status_code=200)

        with HTTMock(mock_200):
            client.request(
                "/one/path", method="GET", params={'key': 'value'}, status_code=200
            )

        with HTTMock(mock_200):
            client.request(
                "/one/path", method="POST", data={'key': 'value'}, status_code=200
            )

        with HTTMock(mock_404):
            client.request("/one/path", method="GET", status_code=404)

        with HTTMock(mock_404):
            with self.assertRaises(CheckmywsError):
                client.request("/one/path", method="GET", status_code=200)

        with HTTMock(mock_404):
            with self.assertRaises(CheckmywsError):
                client.request("/one/path", method="GET", status_code=200)

        client_proxy = CheckmywsClient(proxy="http://127.0.0.1")
        with HTTMock(mock_200):
            client_proxy.request("/one/path", method="GET", status_code=200)

    def test_03_status(self):
        with HTTMock(mock_401):
            with self.assertRaises(CheckmywsError):
                client.status('mycheckid')

        with HTTMock(mock_status):
            data = client.status(check_id)
            self.assertEqual(data['_id'], check_id)

        # Real check
        data = client.status(check_id)
        self.assertEqual(data['_id'], check_id)
        print("URL: %s" % data['url'])

    def test_04_signin(self):
        client = CheckmywsClient(login='unittest', passwd='unittest')

        self.assertNotEqual(client.passwd, 'unittest')
        self.assertEqual(client.authed, False)

        with HTTMock(mock_401):
            with self.assertRaises(CheckmywsError):
                client.signin()

        self.assertEqual(client.authed, False)

        with HTTMock(mock_200):
            client.signin()

        self.assertEqual(client.authed, True)

    def test_05_logout(self):
        client = CheckmywsClient(login='unittest', token='unittest')
        self.assertEqual(client.authed, False)

        with HTTMock(mock_200):
            client.signin()

        self.assertEqual(client.authed, True)

        with HTTMock(mock_401):
            with self.assertRaises(CheckmywsError):
                client.logout()

        self.assertEqual(client.authed, True)

        with HTTMock(mock_200):
            client.logout()

        self.assertEqual(client.authed, False)

    def test_06_checks(self):
        with HTTMock(mock_200_json):
            client.workers()

        with HTTMock(mock_200_json):
            client.checks()

        with HTTMock(mock_200_json):
            client.check('mycheck')

        with HTTMock(mock_200_json):
            client.check('mycheck', {'url': '123'})

        with HTTMock(mock_200_json):
            client.check_create({'url': '123'})

        with HTTMock(mock_200_json):
            client.check_delete('mycheck')

        with HTTMock(mock_200_json):
            client.check_overview('mycheck')

if __name__ == '__main__':
    unittest.main()
