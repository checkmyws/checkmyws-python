# -*- coding: utf-8 -*-

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s %(levelname)s %(message)s',
)

import json
import unittest
import requests

from mock import patch

from checkmyws import CheckmywsClient
from checkmyws import CheckmywsError

client = None


def _build_response_object(status_code=200, content=""):
    resp = requests.Response()
    resp.status_code = status_code
    resp._content = content
    return resp


def _mocked_session(method="GET", status_code=200, content=""):

    method = method.upper()

    def request(*args, **kwargs):
        c = content

        # Check method
        assert method == kwargs.get('method', 'GET')

        # Check requests options
        if method == 'POST':
            data = kwargs.get('data', None)

            if data is not None:
                # Data must be a string
                assert isinstance(data, str)

                # Data must be a JSON string
                json.loads(data)

        # Anyway, Content must be a JSON string (or empty string)
        if not isinstance(c, str):
            c =  json.dumps(c).encode('utf8')

        return _build_response_object(status_code=status_code, content=c)

    mocked = patch.object(
        client.session,
        'request',
        side_effect = request
        )

    return mocked


class TestCase(unittest.TestCase):

    def test_01_init(self):
        global client
        client = CheckmywsClient()

    def test_02_request(self):
        with _mocked_session('get', 200) as mocked:
            client.request("/one/path", method="GET", status_code=200)

        with _mocked_session('post', 200) as mocked:
            client.request("/one/path", method="POST", status_code=200)

        with _mocked_session('get', 200) as mocked:
            client.request(
                "/one/path", method="GET", params={'key': 'value'}, status_code=200
            )

        with _mocked_session('post', 200) as mocked:
            client.request(
                "/one/path", method="POST", data={'key': 'value'}, status_code=200
            )

        with _mocked_session('get', 404) as mocked:
            client.request("/one/path", method="GET", status_code=404)

        with _mocked_session('get', 404) as mocked:
            with self.assertRaises(CheckmywsError):
                client.request("/one/path", method="GET", status_code=200)

        with _mocked_session('get', 404) as mocked:
            with self.assertRaises(CheckmywsError):
                client.request("/one/path", method="GET", status_code=200)

    def test_03_status(self):
        check_id = "3887e18a-28d6-4eac-9eb0-c6d9075e4c7e"
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

        with _mocked_session('get', 401) as mocked:
            with self.assertRaises(CheckmywsError):
                client.status('mycheckid')

        with _mocked_session('get', 200, status) as mocked:
            data = client.status(check_id)
            self.assertEqual(data['_id'], check_id)

if __name__ == '__main__':
    unittest.main()