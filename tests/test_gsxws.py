# -*- coding: utf-8 -*-

import os
import logging
from datetime import date
from unittest import main, skip, TestCase

from gsxws.objectify import parse
from gsxws.products import Product
from gsxws import repairs, escalations


class TestEscalationFunctions(TestCase):
    @skip("Skip")
    def setUp(self):
        from gsxws.core import connect
        logging.basicConfig(level=logging.DEBUG)
        env = os.environ
        connect(env['GSX_USER'], env['GSX_PASSWORD'], env['GSX_SOLDTO'], env['GSX_ENV'])
        esc = escalations.Escalation()
        esc.shipTo = env['GSX_SHIPTO']
        esc.issueTypeCode = 'WS'
        esc.notes = 'This is a test'
        self.escalation = esc.create()

    def test_create_general_escalation(self):
        self.assertTrue(self.escalation.escalationId)

    def test_update_general_escalation(self):
        esc = escalations.Escalation()
        esc.escalationId = self.escalation.escalationId
        esc.status = escalations.STATUS_CLOSED
        result = esc.update()
        self.assertEqual(result.updateStatus, 'SUCCESS')

    def test_attach_general_escalation(self):
        esc = escalations.Escalation()
        esc.escalationId = self.escalation.escalationId
        esc.attachment = escalations.FileAttachment('/tmp/logo.png')
        result = esc.update()
        self.assertEqual(result.updateStatus, 'SUCCESS')

    def test_lookup_general_escalation(self):
        esc = escalations.Escalation()
        esc.escalationId = self.escalation.escalationId
        result = esc.lookup()
        self.assertEqual(result.escalationType, 'GSX Help')


class TestRepairFunctions(TestCase):
    @skip("Skip")
    def test_whole_unit_exchange(self):
        from gsxws.core import connect
        logging.basicConfig(level=logging.DEBUG)
        connect('', '', '', 'it')
        rep = repairs.WholeUnitExchange()
        rep.serialNumber = ''
        rep.unitReceivedDate = '08/12/2013'
        rep.unitReceivedTime = '11:00 am'
        rep.shipTo = ''
        rep.poNumber = ''
        rep.symptom = 'test'
        rep.diagnosis = 'test'
        customer = repairs.Customer(emailAddress='test@example.com')
        customer.firstName = 'First Name'
        customer.lastName = 'Last Name'
        customer.addressLine1 = 'Address Line 1'
        customer.primaryPhone = '0123456789'
        customer.city = 'Test'
        customer.zipCode = '12345'
        customer.state = 'Test'
        customer.country = 'US'
        rep.customerAddress = customer
        part = repairs.RepairOrderLine()
        part.partNumber = '661-5571'
        rep.orderLines = [part]
        rep.create()


class TestWarrantyFunctions(TestCase):
    def setUp(self):
        self.data = parse('tests/fixtures/warranty_status.xml',
                          'warrantyDetailInfo')

    def test_purchase_date(self):
        self.assertIsInstance(self.data.estimatedPurchaseDate, date)

    def test_config_description(self):
        self.assertEqual(self.data.configDescription, 'IPHONE 4,16GB BLACK')

    def test_limited_warranty(self):
        self.assertTrue(self.data.limitedWarranty)

    def test_parts_covered(self):
        self.assertIsInstance(self.data.partCovered, bool)
        self.assertTrue(self.data.partCovered)


class TestOnsiteCoverage(TestCase):
    def setUp(self):
        from gsxws.core import connect
        logging.basicConfig(level=logging.DEBUG)
        env = os.environ
        connect(env['GSX_USER'], env['GSX_PASSWORD'], env['GSX_SOLDTO'], env['GSX_ENV'])
        self.product = Product('XXXXXXXXXXX')
        self.product.warranty()

    def test_has_onsite(self):
        self.assertTrue(self.product.has_onsite)

    def test_coverage(self):
        self.assertTrue(self.product.parts_and_labor_covered)

    def test_is_vintage(self):
        self.assertFalse(self.product.is_vintage)


class TestActivation(TestCase):
    def setUp(self):
        self.data = parse('tests/fixtures/ios_activation.xml',
                          'activationDetailsInfo')

    def test_unlock_date(self):
        self.assertIsInstance(self.data.unlockDate, date)

    def test_unlocked(self):
        self.assertIs(type(self.data.unlocked), bool)
        self.assertTrue(self.data.unlocked)

        p = Product()
        self.assertTrue(p.is_unlocked(self.data))


class TestPartsLookup(TestCase):
    def setUp(self):
        self.data = parse('tests/fixtures/parts_lookup.xml',
                          'PartsLookupResponse')
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
        self.data = parse('tests/fixtures/onsite_dispatch_detail.xml',
                          'onsiteDispatchDetails')

    def test_details(self):
        self.assertEqual(self.data.dispatchId, 'G101260028')

    def test_address(self):
        self.assertEqual(self.data.primaryAddress.zipCode, 85024)
        self.assertEqual(self.data.primaryAddress.firstName, 'Christopher')

    def test_orderlines(self):
        self.assertIsInstance(self.data.dispatchOrderLines.isSerialized, bool)


class TestCarryinRepairDetail(TestCase):
    def setUp(self):
        self.data = parse('tests/fixtures/repair_details_ca.xml',
                          'lookupResponseData')

    def test_details(self):
        self.assertEqual(self.data.dispatchId, 'G2093174681')

    def test_unicode_name(self):
        self.assertEqual(self.data.primaryAddress.firstName, u'Ääkköset')


if __name__ == '__main__':
    main()
