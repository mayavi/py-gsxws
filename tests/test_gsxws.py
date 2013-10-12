# -*- coding: utf-8 -*-

import logging
from datetime import date
from os import environ as env

from unittest import main, skip, TestCase

from gsxws.objectify import parse
from gsxws.products import Product
from gsxws import repairs, escalations, lookups, GsxError, ServicePart


class RemoteTestCase(TestCase):
    def setUp(self):
        from gsxws.core import connect
        connect(env['GSX_USER'],
                env['GSX_PASSWORD'],
                env['GSX_SOLDTO'],
                env['GSX_ENV'])


class TestCoreFunctions(TestCase):
    def test_dump(self):
        rep = repairs.Repair(blaa=u'ääöö')
        part = repairs.RepairOrderLine()
        part.partNumber = '661-5571'
        rep.orderLines = [part]
        self.assertRegexpMatches(rep.dumps(), '<GsxObject><blaa>ääöö</blaa><orderLines>')


class TestErrorFunctions(TestCase):
    def setUp(self):
        xml = open('tests/fixtures/multierror.xml', 'r').read()
        self.data = GsxError(xml=xml)

    def test_code(self):
        self.assertEqual(self.data.errors['RPR.ONS.025'], 
                        'This unit is not eligible for an Onsite repair from GSX.')

    def test_message(self):
        self.assertRegexpMatches(self.data.message, 'Multiple error messages exist.')


class TestLookupFunctions(RemoteTestCase):
    def test_component_check(self):
        l = lookups.Lookup(serialNumber=env['GSX_SN'])
        l.repairStrategy = "CA"
        l.shipTo = env['GSX_SHIPTO']
        r = l.component_check()
        self.assertFalse(r.eligibility)

    def test_component_check_with_parts(self):
        l = lookups.Lookup(serialNumber=env['GSX_SN'])
        l.repairStrategy = "CA"
        l.shipTo = env['GSX_SHIPTO']
        part = ServicePart('661-5502')
        part.symptomCode = 'H06'
        r = l.component_check([part])
        self.assertFalse(r.eligibility)


class TestEscalationFunctions(RemoteTestCase):
    @skip("Skip")
    def setUp(self):
        super(TestEscalationFunctions, self).setUp()
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


class TestRepairFunctions(RemoteTestCase):
    @skip("Skip")
    def test_whole_unit_exchange(self):
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


class TestPartFunction(RemoteTestCase):
    def test_product_parts(self):
        parts = Product(env['GSX_SN']).parts()
        self.assertIsInstance(parts[0].partNumber, basestring)


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


class TestOnsiteCoverage(RemoteTestCase):
    def setUp(self):
        super(TestOnsiteCoverage, self).setUp()
        self.product = Product(env['GSX_SN'])
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

        p = Product(env['GSX_SN'])
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


class TestRepairUpdate(RemoteTestCase):
    def setUp(self):
        super(TestRepairUpdate, self).setUp()
        self.dispatchId = 'G135934345'
        self.repair = repairs.CarryInRepair(self.dispatchId)

    def test_set_repair_status(self):        
        result = self.repair.set_status('BEGR')
        self.assertEqual(result.confirmationNumber, self.dispatchId)

    def test_set_repair_techid(self):
        result = self.repair.set_techid('XXXXX')
        self.assertEqual(result.confirmationNumber, self.dispatchId)

class TestCarryinRepairDetail(TestCase):
    def setUp(self):
        self.data = parse('tests/fixtures/repair_details_ca.xml',
                          'lookupResponseData')

    def test_details(self):
        self.assertEqual(self.data.dispatchId, 'G2093174681')

    def test_unicode_name(self):
        self.assertEqual(self.data.primaryAddress.firstName, u'Ääkköset')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
