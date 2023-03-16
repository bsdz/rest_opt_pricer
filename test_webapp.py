""" Copyright (C) 2023 Blair Azzopardi 

Tests for webapp.
"""

import unittest
from pathlib import Path
import json

from aiohttp.test_utils import AioHTTPTestCase
from aiohttp import FormData
import pandas as pd

from webapp import app, get_expiry

root_dir = Path(__file__).parent


class FunctionsTestCase(unittest.TestCase):
    def test_expiry(self):
        # take these from brief, although correct typo for HH year
        self.assertEqual(get_expiry("BRN", "Jan24"), pd.Timestamp("2023-11-30"))
        self.assertEqual(get_expiry("HH", "Mar24"), pd.Timestamp("2024-02-29"))

class WebAppTestCase(AioHTTPTestCase):

    async def get_application(self):
        return app

    async def test_sequence(self):
        # no market data to start with
        async with self.client.request("GET", "/marketdata/get") as resp:
            self.assertEqual(resp.status, 200)
            text = await resp.text()
        self.assertEqual("{}", text)

        # upload data
        sample_file = root_dir / "market_data.json"
        data = FormData()
        data.add_field('data',
                    sample_file.open('rb'),
                    filename=sample_file.name,
                    content_type='application/json')

        async with self.client.post("/marketdata/put", data=data) as resp:
            self.assertEqual(resp.status, 200)
            text = await resp.text()
        self.assertEqual('{"message": "success"}', text)


        # check market data uploaded
        async with self.client.request("GET", "/marketdata/get") as resp:
            self.assertEqual(resp.status, 200)
            text = await resp.text()
        self.assertIn("BRN", text)
        self.assertIn("HH", text)

        # check some pricing
        async with self.client.request("GET", "/optionpricing/european/BRN/Jan24/Call/100") as resp:
            self.assertEqual(resp.status, 200)
            text = await resp.text()
        dct = json.loads(text)
        self.assertIsInstance(dct["premium"], float)
        self.assertGreater(dct["premium"],  0)
        


if __name__ == "__main__":
    unittest.main()