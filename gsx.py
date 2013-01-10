#coding=utf-8

import re
import os
import json
import base64
import suds
from suds.client import Client
from datetime import date, time

import logging
logging.basicConfig(level=logging.INFO)

logging.getLogger('suds.client').setLevel(logging.DEBUG)

CLIENT = None
SESSION = dict()          # module-level variable

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
        self.dt = self.__make_type(new_dt)

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
            self.request_dt = self.__make_type(new_dt)

        setattr(self.request_dt, field, self.dt)

    def submit(self, method):
        setattr(self.request_dt, 'userSession', SESSION)

        f = getattr(CLIENT.service, method)
        result = f(self.request_dt)
        return result

    def __make_type(self, new_dt):
        return CLIENT.factory.create(new_dt)

    def _process(self, data):
        """
        Tries to coerce some types to their Python counterparts
        """
        for k, v in data:
            # decode binary data
            if k in ['packingList', 'proformaFileData', 'returnLabelFileData']:
                v = base64.b64decode(v)
            
            if isinstance(v, basestring):
                # convert dates to native Python
                if re.search('^\d{2}/\d{2}/\d{2}$', v):
                    m, d, y = v.split('/')
                    v = date(2000+int(y), int(m), int(d)).isoformat()

                # strip currency prefix and munge into float
                if re.search('Price$', k):
                    v = float(re.sub('[A-Z ,]', '', v))

            setattr(data, k, v)

        return data

class CompTia:
    """
    Stores and accesses CompTIA codes.
    This should really be fetched from GSX, but suds gives this error:
    suds.TypeNotFound: Type not found: 'comptiaDescription'
    when calling CompTIACodes()...
    """
    def __init__(self):
        df = open(os.path.join(os.path.dirname(__file__), 'comptia.json'))
        self.data = json.load(df)

    def symptoms(self, component=None):
        symptoms = self.data['symptoms']
        return symptoms[component] if component else symptoms

    def modifiers(self):
        return self.data['modifiers']

class GsxError(suds.WebFault):
    def __init__(self, message, code=None):
        super(GsxError, self).__init__()
        self.code = code
        sys.stderr.write("%s\n" % message)

    def __unicode__(self):
        return self.message

class Lookup(GsxObject):
    def parts(self):
        """
        The Parts Lookup API allows users to access part and part pricing data prior to 
        creating a repair or order. Parts lookup is also a good way to search for 
        part numbers by various attributes of a part
        (config code, EEE code, serial number, etc.). 
        """
        dt = CLIENT.factory.create('ns0:partsLookupRequestType')
        dt.userSession = SESSION
        dt.lookupRequestData = self.data
        result = CLIENT.service.PartsLookup(dt)
        return result.parts

    def repairs(self):
        dt = CLIENT.factory.create('ns6:repairLookupInfoType')
        dt.serialNumber = self.data['serialNumber']
        request = CLIENT.factory.create('ns1:repairLookupRequestType')
        request.userSession = SESSION
        request.lookupRequestData = dt
        result = CLIENT.service.RepairLookup(request)
        return result.lookupResponseData

class Diagnostics(GsxObject):
    def fetch(self):
        """
        The Fetch Repair Diagnostics API allows the service providers/depot/carriers 
        to fetch MRI/CPU diagnostic details from the Apple Diagnostic Repository OR 
        diagnostic test details of iOS Devices.
        The ticket is generated within GSX system.
        """
        if 'alternateDeviceId' in self.data:
            self.set_type('ns7:fetchIOSDiagnosticRequestDataType')
            self.set_request('ns3:fetchIOSDiagnosticRequestType', 'lookupRequestData')
            result = self.submit('FetchIOSDiagnostic')
        else:
            self.set_request('ns3:fetchRepairDiagnosticRequestType', 'lookupRequestData')

class Returns(GsxObject):
    def get_report(self):
        """
        The Return Report API returns a list of all parts that are returned 
        or pending for return, based on the search criteria. 
        """

    def get_label(self):
        """
        The Return Label API retrieves the Return Label for a given Return Order Number.
        """

    def get_proforma(self):
        """
        The View Bulk Return Proforma API allows you to view 
        the proforma label for a given Bulk Return Id.
        You can create a parts bulk return by using the Register Parts for Bulk Return API. 
        """

    def register_parts(self):
        """
        The Register Parts for Bulk Return API creates a bulk return for 
        the registered parts.
        The API returns the Bulk Return Id with the packing list.
        """

    def get_pending(self):
        """
        The Parts Pending Return API returns a list of all parts that 
        are pending for return, based on the search criteria. 
        """

class Part(GsxObject):
    def lookup(self):
        lookup = Lookup(**self.data)
        return lookup.parts()

class Escalation(GsxObject):
    def create(self):
        """
        The Create General Escalation API allows users to create 
        a general escalation in GSX. The API was earlier known as GSX Help.
        """
        self.set_type('ns6:createGenEscRequestDataType')
        self.set_request('ns1:createGenEscRequestType', 'escalationRequest')
        result = self.submit('CreateGeneralEscalation')
        return result.escalationConfirmation

    def update(self):
        """
        The Update General Escalation API allows Depot users to 
        update a general escalation in GSX.
        """
        self.set_type('ns6:updateGeneralEscRequestDataType')
        self.set_request('ns1:updateGeneralEscRequestType', 'escalationRequest')
        result = self.submit('UpdateGeneralEscalation')
        return result.escalationConfirmation

class Repair(GsxObject):
    
    dt = 'ns6:repairLookupInfoType'
    request_dt = 'ns1:repairLookupRequestType'

    def __init__(self, *args, **kwargs):
        super(Repair, self).__init__()
        self.data = kwargs

    def create_carryin(self):
        """
        The Parts Pending Return API returns a list of all parts that 
        are pending for return, based on the search criteria. 
        """
        self.set_type('ns2:emeaAspCreateCarryInRepairDataType')
        ca = CLIENT.factory.create('ns7:addressType')
        self.dt.customerAddress = self.data['customerAddress']
        self.set_request('ns2:carryInRequestType', 'repairData')
        result = self.submit('CreateCarryInRepair')
        print result

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

    def update_carryin(self):
        """
        The Update Carry-In Repair API allows the service providers 
        to update the existing  open carry-in repairs. 
        This API assists in addition/deletion of parts and addition of notes to a repair. 
        On successful update, the repair confirmation number and 
        quote for any newly added parts  would be returned.
        In case of any validation error or unsuccessful update, a fault code is issued.

        Carry-In Repair Update Status Codes:
        AWTP    Awaiting Parts
        AWTR    Parts Allocated
        BEGR    In Repair
        RFPU    Ready for Pickup
        """
        pass

    def lookup(self):
        """
        The Repair Lookup API mimics the front-end repair search functionality.
        It fetches up to 2500 repairs in a given criteria.
        Subsequently, the extended Repair Status API can be used 
        to retrieve more details of the repair. 
        """
        for k, v in self.data.items():
            setattr(self.dt, k, v)

        self.set_request(field='lookupRequestData')
        results = self.submit('RepairLookup')
        return results

    def mark_complete(self):
        """
        The Mark Repair Complete API allows a single or an array of 
        repair confirmation numbers to be submitted to GSX to be marked as complete.
        """
        pass

    def delete(self):
        """
        The Delete Repair API allows the service providers to delete 
        the existing GSX Initiated Carry-In, Return Before Replace & Onsite repairs 
        which are in Declined-Rejected By TSPS Approver state, 
        that do not have an active repair id.
        """
        pass

    def get_status():
        """
        The Repair Status API retrieves the status
        for the submitted repair confirmation number(s).
        """
        pass

    def get_details(self):
        dt = CLIENT.factory.create('ns0:repairDetailsRequestType')
        dt.dispatchId = self.data['dispatchId']
        dt.userSession = SESSION
        results = CLIENT.service.RepairDetails(dt)

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

    def __init__(self, sn):
        super(Product, self).__init__()
        self.dt.serialNumber = sn
        self.sn = sn
        self.lookup = Lookup(serialNumber=self.sn)

    def get_model(self):
        """
        This API allows Service Providers/Carriers to fetch
        Product Model information for the given serial number.
        """
        self.set_request('ns3:fetchProductModelRequestType', 'productModelRequest')
        result = self.submit('FetchProductModel')
        return result

    def get_warranty(self, date_received=None, parts=[]):
        """
        The Warranty Status API retrieves the same warranty details
        displayed on the GSX Coverage screen.
        If part information is provided, the part warranty information is returned.
        If you do not provide the optional part information in the
        warranty status request, the unit level warranty information is returned.
        """
        self.set_request('ns3:warrantyStatusRequestType', 'unitDetail')
        result = self.submit('WarrantyStatus')
        return self._process(result.warrantyDetailInfo)

    def get_activation(self):
        """
        The Fetch iOS Activation Details API is used to 
        fetch activation details of iOS Devices. 
        """
        dt = CLIENT.factory.create('ns3:fetchIOSActivationDetailsRequestType')
        dt.serialNumber = self.sn
        dt.userSession = SESSION
        result = CLIENT.service.FetchIOSActivationDetails(dt)
        return result.activationDetailsInfo

    def get_parts(self):
        return self.lookup.parts()

    def get_repairs(self):
        return self.lookup.repairs()

def init(env='ut', region='emea'):
    global CLIENT

    envs = ('pr', 'it', 'ut',)
    hosts = {'pr': 'ws2', 'it': 'wsit', 'ut': 'wsut'}

    if env not in envs:
        raise ValueError('Environment should be one of: %s' % ','.join(envs))

    url = 'https://gsx{env}.apple.com/wsdl/{region}Asp/gsx-{region}Asp.wsdl'
    url = url.format(env=hosts[env], region=region)

    CLIENT = Client(url)

def connect(user_id, password, sold_to, lang='en', tz='CEST', 
    env='ut', region='emea'):
    global SESSION
    
    SESSION = {}

    init(env, region)

    account = CLIENT.factory.create('ns3:authenticateRequestType')

    account.userId = user_id
    account.password = password
    account.languageCode = lang
    account.userTimeZone = tz
    account.serviceAccountNo = sold_to

    result = CLIENT.service.Authenticate(account)
    SESSION['userSessionId'] = result.userSessionId

    return SESSION

def logout():
    CLIENT.service.Logout()

if __name__ == '__main__':
    import json
    import sys
    #connect(*sys.argv[1:4])
    #f = 'tests/create_carryin_repair.json'
    #f = 'tests/update_escalation.json'
    #fp = open(f, 'r')
    #data = json.load(fp)
    