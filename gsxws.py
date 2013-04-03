#!/usr/bin/env python

#coding=utf-8

"""
Copyright (c) 2012, Filipp Lepalaan All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, 
this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, 
this list of conditions and the following disclaimer in the documentation 
and/or other materials provided with the distribution.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES 
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; 
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED 
AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY 
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import re
import os
import json
import suds
import base64
import logging
import urllib
import urlparse
import tempfile

from suds.client import Client
import xml.etree.ElementTree as ET
from datetime import datetime, date, time

# Must use a few module-level global variables
CLIENT = None
SESSION = dict()
LOCALE = 'en_XXX'

TIMEZONES = (
    ('GMT', 'UTC (Greenwich Mean Time)'),
    ('PDT', 'UTC - 7h (Pacific Daylight Time)'),
    ('PST', 'UTC - 8h (Pacific Standard Time)'),
    ('CDT', 'UTC - 5h (Central Daylight Time)'),
    ('CST', 'UTC - 6h (Central Standard Time)'),
    ('EDT', 'UTC - 4h (Eastern Daylight Time)'),
    ('EST', 'UTC - 5h (Eastern Standard Time)'),
    ('CEST', 'UTC + 2h (Central European Summer Time)'),
    ('CET', 'UTC + 1h (Central European Time)'),
    ('JST', 'UTC + 9h (Japan Standard Time)'),
    ('IST', 'UTC + 5.5h (Indian Standard Time)'),
    ('CCT', 'UTC + 8h (Chinese Coast Time)'),
    ('AEST', 'UTC + 10h (Australian Eastern Standard Time)'),
    ('AEDT', 'UTC + 11h (Australian Eastern Daylight Time)'),
    ('ACST', 'UTC + 9.5h (Austrailian Central Standard Time)'),
    ('ACDT', 'UTC + 10.5h (Australian Central Daylight Time)'),
    ('NZST', 'UTC + 12h (New Zealand Standard Time)'),
)

REGIONS = (
    ('002', 'Asia/Pacific'),
    ('003', 'Japan'),
    ('004', 'Europe'),
    ('005', 'United States'),
    ('006', 'Canadia'),
    ('007', 'Latin America'),
)

REGION_CODES = ('apac', 'am', 'la', 'emea',)

ENVIRONMENTS = (
    ('pr', 'Production'), 
    ('ut', 'Development'),
    ('it', 'Testing'),
)

def validate(value, what=None):
    """
    Tries to guess the meaning of value or validate that
    value looks like what it's supposed to be.
    """
    result = None

    if not isinstance(value, basestring):
        raise ValueError('%s is not valid input')

    rex = {
        'partNumber'        : r'^([A-Z]{1,2})?\d{3}\-?(\d{4}|[A-Z]{2})(/[A-Z])?$',
        'serialNumber'      : r'^[A-Z0-9]{11,12}$',
        'eeeCode'           : r'^[A-Z0-9]{3,4}$',
        'returnOrder'       : r'^7\d{9}$',
        'repairNumber'      : r'^\d{12}$',
        'dispatchId'        : r'^G\d{9}$',
        'alternateDeviceId' : r'^\d{15}$',
        'diagnosticEventNumber': r'^\d{23}$',
        'productName'       : r'^i?Mac',
    }
    
    for k, v in rex.items():
        if re.match(v, value):
            result = k

    return (result == what) if what else result

def get_format(locale=LOCALE):
    df = open(os.path.join(os.path.dirname(__file__), 'langs.json'), 'r')
    data = json.load(df)

    return data[locale]

class GsxObject(object):
    """
    The thing that gets sent to and from GSX
    """
    dt          = 'ns3:authenticateRequestType'   # The GSX datatype matching this object
    request_dt  = 'ns3:authenticateRequestType'   # The GSX datatype matching this request
    method      = 'Authenticate'                  # The SOAP method to call on the GSX server

    def __init__(self, *args, **kwargs):
        self.data = kwargs
        self.dt = CLIENT.factory.create(self.dt)
        self.request_dt = CLIENT.factory.create(self.request_dt)

    def set_method(self, new_method):
        self.method = new_method

    def set_type(self, new_dt):
        """
        Sets the object's primary data type to new_dt
        """
        self.dt = self._make_type(new_dt)

        try:
            for k, v in self.data.items():
                setattr(self.dt, k, v)
        except Exception, e:
            pass

    def set_request(self, new_dt=None, field=None):
        """
        Sets the field of this object's request datatype to the new value
        """
        if new_dt:
            self.request_dt = self._make_type(new_dt)

        setattr(self.request_dt, field, self.dt)

    def submit(self, method, data, attr=None):
        """
        Submits the SOAP envelope
        """
        f = getattr(CLIENT.service, method)
        
        try:
            result = f(data)
            return getattr(result, attr) if attr else result
        except suds.WebFault, e:
            raise GsxError(fault=e)

    def _make_type(self, new_dt):
        """
        Creates the top-level datatype for the API call
        """
        dt = CLIENT.factory.create(new_dt)

        if SESSION:
            dt.userSession = SESSION

        return dt

    def _process(self, data):
        """
        Tries to coerce some types to their Python counterparts
        """
        for k, v in data:
            # decode binary data
            if k in ['packingList', 'proformaFileData', 'returnLabelFileData']:
                v = base64.b64decode(v)
            
            if isinstance(v, basestring):
                # convert dates to native Python types
                if re.search('^\d{2}/\d{2}/\d{2}$', v):
                    m, d, y = v.split('/')
                    v = date(2000+int(y), int(m), int(d))

                # strip currency prefix and munge into float
                if re.search('Price$', k):
                    v = float(re.sub('[A-Z ,]', '', v))

            setattr(data, k, v)

        return data

    def get_response(self, xml_el):

        if isinstance(xml_el, list):
            out = []
            for i in xml_el:
                out.append(self.get_response(i))

            return out

        if isinstance(xml_el, dict):
            out = []
            for i in xml_el.items():
                out.append(self.get_response(i))

            return out

        class ReturnData(dict):
            pass

        rd = ReturnData()
        
        for r in xml_el.iter():
            k, v = r.tag, r.text
            if k in ['packingList', 'proformaFileData', 'returnLabelFileData']:
                v = base64.b64decode(v)

            setattr(rd, k, v)

        return rd

    def __getattr__(self, name):
        return self.data[name]

class Content(GsxObject):
    def fetch_image(self, url):
        '''
        The Fetch Image API allows users to get the image file from GSX, 
        for the content articles, using the image URL. 
        The image URLs will be obtained from the image html tags in the data from all content APIs. 
        '''
        dt = self._make_type('ns3:fetchImageRequestType')
        dt.imageRequest = {'imageUrl': url}
        return self.submit('FetchImage', dt, 'contentResponse')

class CompTIA(object):
    '''
    Stores and accesses CompTIA codes.
    '''
    
    MODIFIERS = (
        ("A", "Not Applicable"),
        ("B", "Continuous"),
        ("C", "Intermittent"),
        ("D", "Fails After Warm Up"),
        ("E", "Environmental"),
        ("F", "Configuration: Peripheral"),
        ("G", "Damaged"),
    )
    
    GROUPS = (
        ('0', 'General'),
        ('1', 'Visual'),
        ('2', 'Displays'),
        ('3', 'Mass Storage'),
        ('4', 'Input Devices'),
        ('5', 'Boards'),
        ('6', 'Power'),
        ('7', 'Printer'),
        ('8', 'Multi-function Device'),
        ('9', 'Communication Devices'),
        ('A', 'Share'),
        ('B', 'iPhone'),
        ('E', 'iPod'),
        ('F', 'iPad'),
    )
    
    def __init__(self):
        '''
        Initialize CompTIA symptoms from JSON file
        '''
        df = open(os.path.join(os.path.dirname(__file__), 'comptia.json'))
        self.data = json.load(df)
        
    def fetch(self):
        '''
        "The CompTIA Codes Lookup API retrieves a list of CompTIA groups and modifiers."

        Here we must resort to raw XML parsing since SUDS throws this:
        suds.TypeNotFound: Type not found: 'comptiaDescription'
        when calling CompTIACodes()...
        '''
        CLIENT.set_options(retxml=True)
        dt = CLIENT.factory.create('ns3:comptiaCodeLookupRequestType')
        dt.userSession = SESSION

        try:
            xml = CLIENT.service.CompTIACodes(dt)
        except suds.WebFault, e:
            raise GsxError(fault=e)
        
        root = ET.fromstring(xml).findall('.//%s' % 'comptiaInfo')[0]

        for el in root.findall('.//comptiaGroup'):
            group = {}
            comp_id = el[0].text
            
            for ci in el.findall('comptiaCodeInfo'):
                group[ci[0].text] = ci[1].text
            
            self.data[comp_id] = group

        return self.data

    def symptoms(self, component=None):
        '''
        Returns all known CompTIA symptom codes or just the ones
        belonging to the given component code.
        '''
        r = dict()
        
        for g, codes in self.data.items():
            r[g] = list()
            for k, v in codes.items():
                r[g].append((k, v,))
            
        return r[component] if component else r

class GsxResponse(dict):
    """
    This contains the data returned by a raw GSX query
    """
    def __getattr__(self, item):
        return self.__getitem__(item)

    def __setattr__(self, item, value):
        self.__setitem__(item, value)

    @classmethod
    def Process(cls, node):
        nodedict = cls()
        
        for child in node:
            k, v = child.tag, child.text
            newitem = cls.Process(child)

            if nodedict.has_key(k):
                # found duplicate tag
                if isinstance(nodedict[k], list):
                    # append to existing list
                    nodedict[k].append(newitem)
                else:
                    # convert to list
                    nodedict[k] = [nodedict[k], newitem]
            else:
                # unique tag -> set the dictionary
                nodedict[k] = newitem

            if k in ('packingList', 'proformaFileData', 'returnLabelFileData'):
                nodedict[k] = base64.b64decode(v)

            if isinstance(v, basestring):
                # convert dates to native Python type
                if re.search('^\d{2}/\d{2}/\d{2}$', v):
                    m, d, y = v.split('/')
                    v = date(2000+int(y), int(m), int(d)).isoformat()

                # strip currency prefix and munge into float
                if re.search('Price$', k):
                    v = float(re.sub('[A-Z ,]', '', v))

                # Convert timestamps to native Python type
                # 18-Jan-13 14:38:04
                if re.search('TimeStamp$', k):
                    v = datetime.strptime(v, '%d-%b-%y %H:%M:%S')

                # convert Y and N to corresponding boolean
                if re.search('^[YN]$', k):
                    v = (v == 'Y')

                nodedict[k] = v

        return nodedict

class GsxError(Exception):
    def __init__(self, message=None, code=None, fault=None):
        if isinstance(fault, suds.WebFault):
            self.code = fault.fault.faultcode
            self.message=fault.fault.faultstring
        else:
            self.code = code
            self.message = message
        
        self.data = (self.code, self.message)

    def __getitem__(self, idx):
        return self.data[idx]
        
    def __repr__(self):
        print self.data

    def __str__(self):
        return self.data[1]

class Lookup(GsxObject):
    def parts(self):
        """
        The Parts Lookup API allows users to access part and part pricing data prior to 
        creating a repair or order. Parts lookup is also a good way to search for 
        part numbers by various attributes of a part
        (config code, EEE code, serial number, etc.). 
        """
        dt = self._make_type("ns0:partsLookupRequestType")
        dt.lookupRequestData = self.data
        return self.submit("PartsLookup", dt, "parts")

    def repairs(self):
        """
        The Repair Lookup API mimics the front-end repair search functionality.
        It fetches up to 2500 repairs in a given criteria.
        Subsequently, the extended Repair Status API can be used 
        to retrieve more details of the repair.
        """
        dt = CLIENT.factory.create('ns6:repairLookupInfoType')
        request = CLIENT.factory.create('ns1:repairLookupRequestType')
        request.userSession = SESSION
        request.lookupRequestData = self.data
        return self.submit("RepairLookup", request, "lookupResponseData")

class Diagnostics(GsxObject):
    def fetch(self):
        """
        The Fetch Repair Diagnostics API allows the service providers/depot/carriers 
        to fetch MRI/CPU diagnostic details from the Apple Diagnostic Repository OR 
        diagnostic test details of iOS Devices.
        The ticket is generated within GSX system.
        """
        # Using raw XML to avoid TypeNotFound: Type not found: 'toolID' or operationID
        CLIENT.set_options(retxml=True)
        if "alternateDeviceId" in self.data:
            dt = self._make_type("ns3:fetchIOSDiagnosticRequestType")
            dt.lookupRequestData = self.data
            
            try:
                result = CLIENT.service.FetchIOSDiagnostic(dt)
            except suds.WebFault, e:
                raise GsxError(fault=e)
                
            root = ET.fromstring(result).findall('*//%s' % 'FetchIOSDiagnosticResponse')[0]
        else:
            dt = self._make_type('ns3:fetchRepairDiagnosticRequestType')
            dt.lookupRequestData = self.data
            
            try:
                result = CLIENT.service.FetchRepairDiagnostic(dt)
            except suds.WebFault, e:
                raise GsxError(fault=e)

            root = ET.fromstring(result).findall('*//%s' % 'FetchRepairDiagnosticResponse')[0]
        
        return GsxResponse.Process(root)

class Order(GsxObject):
    def __init__(self, type='stocking', *args, **kwargs):
        super(Order, self).__init__(*args, **kwargs)
        self.data['orderLines'] = list()

    def add_part(self, part_number, quantity):
        self.data['orderLines'].append({
            'partNumber': part_number, 'quantity': quantity
            })

    def submit(self):
        dt = CLIENT.factory.create('ns1:createStockingOrderRequestType')
        dt.userSession = SESSION
        dt.orderData = self.data

        try:
            result = CLIENT.service.CreateStockingOrder(dt)
            return result.orderConfirmation
        except suds.WebFault, e:
            raise GsxError(fault=e)

class Returns(GsxObject):
    def __init__(self, order_number=None, *args, **kwargs):
        super(Returns, self).__init__(*args, **kwargs)
        self.dt.returnOrderNumber = order_number

    def get_report(self):
        """
        The Return Report API returns a list of all parts that are returned 
        or pending for return, based on the search criteria. 
        """
        dt = self._make_type('ns1:returnReportRequestType')
        dt.returnRequestData = self.data

        return self.submit('ReturnReport', dt, 'returnResponseData')

    def get_label(self, part_number):
        """
        The Return Label API retrieves the Return Label for a given Return Order Number.
        (Type not found: 'comptiaCode')
        so we're parsing the raw SOAP response and creating a "fake" return object from that.
        """
        if not validate(part_number, 'partNumber'):
            raise ValueError('%s is not a valid part number' % part_number)

        class ReturnData(dict):
            pass

        rd = ReturnData()

        CLIENT.set_options(retxml=True)

        dt = CLIENT.factory.create('ns1:returnLabelRequestType')
        dt.returnOrderNumber = self.dt.returnOrderNumber
        dt.partNumber = part_number
        dt.userSession = SESSION

        try:
            result = CLIENT.service.ReturnLabel(dt)
        except suds.WebFault, e:
            raise GsxError(fault=e)

        el = ET.fromstring(result).findall('*//%s' % 'returnLabelData')[0]

        for r in el.iter():
            k, v = r.tag, r.text
            if k in ['packingList', 'proformaFileData', 'returnLabelFileData']:
                v = base64.b64decode(v)

            setattr(rd, k, v)

        return rd

    def get_proforma(self):
        """
        The View Bulk Return Proforma API allows you to view 
        the proforma label for a given Bulk Return Id.
        You can create a parts bulk return by using the Register Parts for Bulk Return API. 
        """
        pass

    def register_parts(self):
        """
        The Register Parts for Bulk Return API creates a bulk return for 
        the registered parts.
        The API returns the Bulk Return Id with the packing list.
        """
        pass

    def get_pending(self):
        """
        The Parts Pending Return API returns a list of all parts that 
        are pending for return, based on the search criteria. 
        """
        dt = CLIENT.factory.create('ns1:partsPendingReturnRequestType')
        dt.repairData = self.data
        dt.userSession = SESSION
        
        return self.submit('PartsPendingReturn', dt, 'partsPendingResponse')

class Part(GsxObject):
    def lookup(self):
        lookup = Lookup(**self.data)
        return lookup.parts()

    def fetch_image(self):
        """
        Tries the fetch the product image for this service part
        """
        if self.partNumber is None:
            raise GsxError('Cannot fetch part image without part number')

        url = 'https://km.support.apple.com.edgekey.net/kb/imageService.jsp?image=%s_350_350.gif' % self.partNumber
        p = urlparse.urlparse(url)
        filename = p.query.split('=')[1]
        tmpfile = tempfile.NamedTemporaryFile(suffix=filename)

        try:
            result = urllib.urlretrieve(url, tmpfile.name)
            return result[0]
        except Exception, e:
            GsxError('Failed to fetch part image')

class Escalation(GsxObject):
    def create(self):
        """
        The Create General Escalation API allows users to create 
        a general escalation in GSX. The API was earlier known as GSX Help.
        """
        dt = self._make_type("ns1:createGenEscRequestType")
        dt.escalationRequest = self.data
        return self.submit("CreateGeneralEscalation", dt, "escalationConfirmation")

    def update(self):
        """
        The Update General Escalation API allows Depot users to 
        update a general escalation in GSX.
        """
        dt = self._make_type("ns1:updateGeneralEscRequestType")
        dt.escalationRequest = self.data
        return self.submit("UpdateGeneralEscalation", dt, "escalationConfirmation")

class Repair(GsxObject):
    
    dt = 'ns6:repairLookupInfoType'
    request_dt = 'ns1:repairLookupRequestType'

    def __init__(self, *args, **kwargs):
        super(Repair, self).__init__(*args, **kwargs)
        formats = get_format()

        # native types are not welcome here :)
        for k, v in kwargs.items():
            if isinstance(v, date):
                kwargs[k] = v.strftime(formats['df'])
            if isinstance(v, time):
                kwargs[k] = v.strftime(formats['tf'])
            if isinstance(v, bool):
                kwargs[k] = 'Y' if v else 'N'
        
        self.data = kwargs

    def create_carryin(self):
        """
        GSX validates the information and if all of the validations go through,
        it obtains a quote for the repair and creates the carry-in repair.
        """
        dt = self._make_type('ns2:carryInRequestType')
        dt.repairData = self.data

        return self.submit('CreateCarryInRepair', dt, 'repairConfirmation')
        
    def create_cnd(self):
        """
        The Create CND Repair API allows Service Providers to create a repair 
        whenever the reported issue cannot be duplicated, and the repair 
        requires no parts replacement.
        N01 Unable to Replicate
        N02 Software Update/Issue
        N03 Cable/Component Reseat
        N05 SMC Reset
        N06 PRAM Reset
        N07 Third Party Part
        N99 Other
        """
        pass

    def update_carryin(self, newdata):
        """
        The Update Carry-In Repair API allows the service providers 
        to update the existing  open carry-in repairs. 
        This API assists in addition/deletion of parts and addition of notes 
        to a repair. On successful update, the repair confirmation number and 
        quote for any newly added parts  would be returned.
        In case of any validation error or unsuccessful update, a fault code is issued.

        Carry-In Repair Update Status Codes:
        AWTP    Awaiting Parts
        AWTR    Parts Allocated
        BEGR    In Repair
        RFPU    Ready for Pickup
        """
        dt = self._make_type('ns1:updateCarryInRequestType')
        
        # Merge old and new data (old data should have Dispatch ID)
        dt.repairData = dict(self.data.items() + newdata.items())

        return self.submit('CarryInRepairUpdate', dt, 'repairConfirmation')

    def update_sn(self, parts):
        """
        Description
        The Update Serial Number API allows the service providers to 
        update the module serial numbers. 
        Context:
        The API is not applicable for whole unit replacement 
        serial number entry (see KGB serial update).
        """
        dt = self._make_type('ns1:updateSerialNumberRequestType')
        repairData = {'repairConfirmationNumber': self.data.get('dispatchId')}
        repairData['partInfo'] = parts
        dt.repairData = repairData
        
        return self.submit('UpdateSerialNumber', dt, 'repairConfirmation')

    def update_kgb_sn(self, sn):
        """
        Description:
        The KGB Serial Number Update API is always to be used on 
        whole unit repairs that are in a released state. 
        This API allows users to provide the KGB serial number for the 
        whole unit exchange repairs. It also checks for the privilege 
        to create/ update whole unit exchange repairs 
        before updating the whole unit exchange repair. 
        Context:
        The API is to be used on whole unit repairs that are in a released state. 
        This API can be invoked only after carry-in repair creation API.
        """

        # Using raw XML to avoid:
        # Exception: <UpdateKGBSerialNumberResponse/> not mapped to message part
        CLIENT.set_options(retxml=True)
        dt = self._make_type('ns1:updateKGBSerialNumberRequestType')
        dt.repairConfirmationNumber = self.data['dispatchId']
        dt.serialNumber = sn

        try:
            result = CLIENT.service.KGBSerialNumberUpdate(dt)
        except suds.WebFault, e:
            raise GsxError(fault=e)
            
        root = ET.fromstring(result).findall('*//%s' % 'UpdateKGBSerialNumberResponse')
        return GsxResponse.Process(root[0])

    def lookup(self):
        """
        The Repair Lookup API mimics the front-end repair search functionality.
        It fetches up to 2500 repairs in a given criteria.
        Subsequently, the extended Repair Status API can be used 
        to retrieve more details of the repair. 
        """
        return Lookup(**self.data).repairs()

    def mark_complete(self, numbers=None):
        """
        The Mark Repair Complete API allows a single or an array of 
        repair confirmation numbers to be submitted to GSX to be marked as complete.
        """
        dt = self._make_type('ns1:markRepairCompleteRequestType')
        dt.repairConfirmationNumbers = [self.data['dispatchId']]

        try:
            result = CLIENT.service.MarkRepairComplete(dt)
            return result.repairConfirmationNumbers
        except suds.WebFault, e:
            raise GsxError(fault=e)

    def delete(self):
        """
        The Delete Repair API allows the service providers to delete 
        the existing GSX Initiated Carry-In, Return Before Replace & Onsite repairs 
        which are in Declined-Rejected By TSPS Approver state, 
        that do not have an active repair id.
        """
        pass

    def get_status(self, numbers=None):
        """
        The Repair Status API retrieves the status
        for the submitted repair confirmation number(s).
        """
        dt = self._make_type('ns1:repairStatusRequestType')
        dt.repairConfirmationNumbers = [self.data['dispatchId']]
        result = CLIENT.service.RepairStatus(dt)

        if len(result.repairStatus) == 1:
            return result.repairStatus[0]
        else:
            return result.repairStatus

    def get_details(self):
        """
        The Repair Details API includes the shipment information 
        similar to the Repair Lookup API. 
        """
        dt = self._make_type('ns0:repairDetailsRequestType')
        dt.dispatchId = self.data['dispatchId']
        results = CLIENT.service.RepairDetails(dt)
        details = results.lookupResponseData[0]

        # fix tracking URL if available
        for i, p in enumerate(details.partsInfo):
            try:
                url = re.sub('<<TRKNO>>', p.deliveryTrackingNumber, p.carrierURL)
                details.partsInfo[i].carrierURL = url
            except AttributeError, e:
                pass

        return details

class Communication(GsxObject):
    def get_content():
        """
        The Fetch Communication Content API allows the service providers/depot/carriers
        to fetch the communication content by article ID from the service news channel. 
        """

    def get_articles():
        """
        The Fetch Communication Articles API allows the service partners
        to fetch all the active communication message IDs. 
        """

class Product(GsxObject):
    
    dt = 'ns7:unitDetailType'

    def __init__(self, serialNumber):
        super(Product, self).__init__()
        self.serialNumber = serialNumber
        self.dt.serialNumber = serialNumber
        self.lookup = Lookup(serialNumber=self.serialNumber)

    def get_model(self):
        """
        This API allows Service Providers/Carriers to fetch
        Product Model information for the given serial number.
        """
        #self.set_request('ns3:fetchProductModelRequestType', 'productModelRequest')
        dt = self._make_type("ns3:fetchProductModelRequestType")
        dt.productModelRequest = self.dt
        result = self.submit('FetchProductModel', dt, "productModelResponse")
        return result

    def get_warranty(self, date_received=None, parts=[]):
        """
        The Warranty Status API retrieves the same warranty details
        displayed on the GSX Coverage screen.
        If part information is provided, the part warranty information is returned.
        If you do not provide the optional part information in the
        warranty status request, the unit level warranty information is returned.
        """
        dt = self._make_type("ns3:warrantyStatusRequestType")
        dt.unitDetail = self.dt
        result = self.submit("WarrantyStatus", dt, "warrantyDetailInfo")
        return self._process(result)


    def get_activation(self):
        """
        The Fetch iOS Activation Details API is used to 
        fetch activation details of iOS Devices. 
        """
        dt = self._make_type('ns3:fetchIOSActivationDetailsRequestType')
        dt.serialNumber = self.serialNumber
        return self.submit('FetchIOSActivationDetails', dt, 'activationDetailsInfo')

    def get_parts(self):
        return self.lookup.parts()

    def get_repairs(self):
        return self.lookup.repairs()

    def get_diagnostics(self):
        diags = Diagnostics(serialNumber=self.serialNumber)
        return diags.fetch()

    def fetch_image(self):
        if not self.imageURL:
            raise GsxError('Cannot fetch product image with image URL')

        try:
            urllib.urlretrieve(self.imageURL)
            return result[0]
        except Exception, e:
            raise GsxError('Failed to fetch product image')

def init(env='ut', region='emea'):
    global CLIENT, REGION_CODES

    envs = ('pr', 'it', 'ut',)
    hosts = {'pr': 'ws2', 'it': 'wsit', 'ut': 'wsut'}

    if region not in REGION_CODES:
        raise ValueError('Region should be one of: %s' % ','.join(REGION_CODES))

    if env not in envs:
        raise ValueError('Environment should be one of: %s' % ','.join(envs))

    url = 'https://gsx{env}.apple.com/wsdl/{region}Asp/gsx-{region}Asp.wsdl'
    url = url.format(env=hosts[env], region=region)

    CLIENT = Client(url)
    CLIENT.options.cache.setduration(weeks=2)

def connect(
        user_id,
        password,
        sold_to, 
        language='en',
        timezone='CEST', 
        environment='ut',
        region='emea',
        locale=LOCALE):
    """
    Establishes connection with GSX Web Services.
    Returns the session ID of the new connection.
    """
    
    global SESSION
    global LOCALE

    SESSION = {}
    LOCALE = LOCALE

    init(environment, region)

    account = CLIENT.factory.create('ns3:authenticateRequestType')

    account.userId = user_id
    account.password = password
    account.languageCode = language
    account.userTimeZone = timezone
    account.serviceAccountNo = sold_to

    try:
        result = CLIENT.service.Authenticate(account)
        SESSION['userSessionId'] = result.userSessionId
        return SESSION
    except suds.WebFault, e:
        raise GsxError(fault=e)

def logout():
    CLIENT.service.Logout()

if __name__ == '__main__':
    import sys
    import json
    import argparse
    
    parser = argparse.ArgumentParser(description='Communicate with GSX Web Services')

    parser.add_argument('user_id')
    parser.add_argument('password')
    parser.add_argument('sold_to')
    parser.add_argument('--language', default='en')
    parser.add_argument('--timezone', default='CEST')
    parser.add_argument('--environment', default='pr')
    parser.add_argument('--region', default='emea')
    
    args = parser.parse_args()
