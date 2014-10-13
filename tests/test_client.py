# -*- coding: utf-8 -*-

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s %(levelname)s %(message)s',
)

import json
import unittest
import requests

from httmock import all_requests, HTTMock

from checkmyws import CheckmywsClient
from checkmyws import CheckmywsError

client = None
check_id = "9597dc65-6a94-4a91-8200-63b1368a7e1c"

@all_requests
def mock_200(url, request):
    return {'status_code': 200, 'content': None}


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

if __name__ == '__main__':
    unittest.main()