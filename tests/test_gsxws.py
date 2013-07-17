# -*- coding: utf-8 -*-

from datetime import date
from unittest import main, TestCase

from gsxws.objectify import parse


class TestWarrantyFunctions(TestCase):
    def setUp(self):
        self.data = parse('tests/fixtures/warranty_status.xml', 'warrantyDetailInfo')

    def test_purchase_date(self):
        self.assertIsInstance(self.data.estimatedPurchaseDate, date)

    def test_config_description(self):
        self.assertEqual(self.data.configDescription, 'IPHONE 4,16GB BLACK')

    def test_limited_warranty(self):
        self.assertTrue(self.data.limitedWarranty)

    def test_parts_covered(self):
        self.assertIsInstance(self.data.partCovered, bool)
        self.assertTrue(self.data.partCovered)


class TestActivation(TestCase):
    def setUp(self):
        self.data = parse('tests/fixtures/ios_activation.xml', 'activationDetailsInfo')

    def test_unlock_date(self):
        self.assertIsInstance(self.data.unlockDate, date)

    def test_unlocked(self):
        self.assertIs(type(self.data.unlocked), bool)
        self.assertTrue(self.data.unlocked)


class TestPartsLookup(TestCase):
    def setUp(self):
        self.data = parse('tests/fixtures/parts_lookup.xml', 'PartsLookupResponse')
        self.part = self.data.parts[0]

    def test_parts(self):
        self.assertEqual(len(self.data.parts), 3)

    def test_exchange_price(self):
        self.assertEqual(self.part.exchangePrice, 14.4)

    def test_stock_price(self):
        self.assertEqual(self.part.stockPrice, 17.1)

    def test_serialized(self):
        self.assertIsInstance(self.part.isSerialized, bool)
        self.assertTrue(self.part.isSerialized)

    def test_description(self):
        self.assertEqual(self.part.partDescription, 'SVC,REMOTE')


class TestOnsiteDispatchDetail(TestCase):
    def setUp(self):
        self.data = parse('tests/fixtures/onsite_dispatch_detail.xml', 'onsiteDispatchDetails')

    def test_details(self):
        self.assertEqual(self.data.dispatchId, 'G101260028')

    def test_address(self):
        self.assertEqual(self.data.primaryAddress.zipCode, 85024)
        self.assertEqual(self.data.primaryAddress.firstName, 'Christopher')

    def test_orderlines(self):
        self.assertIsInstance(self.data.dispatchOrderLines.isSerialized, bool)

if __name__ == '__main__':
    main()
