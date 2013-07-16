# -*- coding: utf-8 -*-

import unittest
from datetime import date

from gsxws.objectify import parse


class TestWarrantyFunctions(unittest.TestCase):
    def setUp(self):
        self.wty = parse('tests/fixtures/warranty_status.xml', 'warrantyDetailInfo')

    def test_purchase_date(self):
        self.assertIsInstance(self.wty.estimatedPurchaseDate.pyval, date)

    def test_config_description(self):
        self.assertEqual(self.wty.configDescription, 'IPHONE 4,16GB BLACK')


if __name__ == '__main__':
    unittest.main()
