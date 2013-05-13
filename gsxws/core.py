"""
Copyright (c) 2013, Filipp Lepalaan All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

- Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice,
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
import json
import base64
import shelve
import os.path
import hashlib
import logging
import httplib
import tempfile
from urlparse import urlparse
import xml.etree.ElementTree as ET

from datetime import date, time, datetime, timedelta

GSX_ENV = "it"
GSX_LANG = "en"
GSX_REGION = "emea"
GSX_LOCALE = "en_XXX"

GSX_SESSION = None

GSX_REGIONS = (
    ('002', "Asia/Pacific"),
    ('003', "Japan"),
    ('004', "Europe"),
    ('005', "United States"),
    ('006', "Canadia"),
    ('007', "Latin America"),
)

GSX_TIMEZONES = (
    ('GMT', "UTC (Greenwich Mean Time)"),
    ('PDT', "UTC - 7h (Pacific Daylight Time)"),
    ('PST', "UTC - 8h (Pacific Standard Time)"),
    ('CDT', "UTC - 5h (Central Daylight Time)"),
    ('CST', "UTC - 6h (Central Standard Time)"),
    ('EDT', "UTC - 4h (Eastern Daylight Time)"),
    ('EST', "UTC - 5h (Eastern Standard Time)"),
    ('CEST', "UTC + 2h (Central European Summer Time)"),
    ('CET', "UTC + 1h (Central European Time)"),
    ('JST', "UTC + 9h (Japan Standard Time)"),
    ('IST', "UTC + 5.5h (Indian Standard Time)"),
    ('CCT', "UTC + 8h (Chinese Coast Time)"),
    ('AEST', "UTC + 10h (Australian Eastern Standard Time)"),
    ('AEDT', "UTC + 11h (Australian Eastern Daylight Time)"),
    ('ACST', "UTC + 9.5h (Austrailian Central Standard Time)"),
    ('ACDT', "UTC + 10.5h (Australian Central Daylight Time)"),
    ('NZST', "UTC + 12h (New Zealand Standard Time)"),
)

REGION_CODES = ('apac', 'am', 'la', 'emea',)

ENVIRONMENTS = (
    ('pr', "Production"),
    ('ut', "Development"),
    ('it', "Testing"),
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
        'partNumber':       r'^([A-Z]{1,2})?\d{3}\-?(\d{4}|[A-Z]{2})(/[A-Z])?$',
        'serialNumber':     r'^[A-Z0-9]{11,12}$',
        'eeeCode':          r'^[A-Z0-9]{3,4}$',
        'returnOrder':      r'^7\d{9}$',
        'repairNumber':     r'^\d{12}$',
        'dispatchId':       r'^G\d{9}$',
        'alternateDeviceId': r'^\d{15}$',
        'diagnosticEventNumber': r'^\d{23}$',
        'productName':      r'^i?Mac',
    }

    for k, v in rex.items():
        if re.match(v, value):
            result = k

    return (result == what) if what else result


def get_formats(locale=GSX_LOCALE):
    filepath = os.path.join(os.path.dirname(__file__), 'langs.json')
    df = open(filepath, 'r')
    return json.load(df).get(locale)


class GsxError(Exception):
    def __init__(self, message=None, xml=None):

        if message is not None:
            raise ValueError(message)

        if xml is not None:
            el = ET.fromstring(xml)
            self.code = el.findtext("*//faultcode")

            if self.code is None:
                raise ValueError("An unexpected error occured")

        self.message = el.findtext("*//faultstring")

    def __unicode__(self):
        return self.message

    def __str__(self):
        return self.message


class GsxCache(object):
    """
    >>> GsxCache('spam').set('eggs').get()
    'eggs'
    """
    shelf = None
    tmpdir = tempfile.gettempdir()
    filename = os.path.join(tmpdir, "gsxws.tmp")

    def __init__(self, key, expires=timedelta(minutes=20)):
        self.key = key
        self.expires = expires
        self.shelf = shelve.open(self.filename, protocol=-1)
        self.now = datetime.now()

        if not self.shelf.get(key):
            # Initialize the key
            self.set(None)

    def get(self):
        try:
            d = self.shelf[self.key]
            if d['expires'] > self.now:
                return d['value']
            else:
                del self.shelf[self.key]
        except KeyError:
            return None

    def set(self, value):
        d = {
            'value': value,
            'expires': self.now + self.expires
        }

        self.shelf[self.key] = d
        return self


class GsxRequest(object):
    "Creates and submits the SOAP envelope"
    env = None
    obj = None      # The GsxObject being submitted
    data = None     # The GsxObject payload in XML format
    body = None     # The Body part of the SOAP envelope

    _request = ""
    _response = ""

    envs = ('pr', 'it', 'ut',)
    REGION_CODES = ('apac', 'am', 'la', 'emea',)

    hosts = {'pr': 'ws2', 'it': 'wsit', 'ut': 'wsut'}
    url = "https://gsx{env}.apple.com/gsx-ws/services/{region}/asp"

    def __init__(self, **kwargs):
        "Construct the SOAP envelope"
        self.objects = []
        self.env = ET.Element("soapenv:Envelope")
        self.env.set("xmlns:core", "http://gsxws.apple.com/elements/core")
        self.env.set("xmlns:glob", "http://gsxws.apple.com/elements/global")
        self.env.set("xmlns:asp", "http://gsxws.apple.com/elements/core/asp")
        self.env.set("xmlns:am", "http://gsxws.apple.com/elements/core/asp/am")
        self.env.set("xmlns:soapenv", "http://schemas.xmlsoap.org/soap/envelope/")

        ET.SubElement(self.env, "soapenv:Header")
        self.body = ET.SubElement(self.env, "soapenv:Body")

        for k, v in kwargs.items():
            self.obj = v
            self._request = k
            self.data = v.to_xml(self._request)
            self._response = k.replace("Request", "Response")

    def _submit(self, method, response=None):
        "Construct and submit the final SOAP message"
        global GSX_ENV, GSX_REGION, GSX_SESSION

        root = ET.SubElement(self.body, self.obj._namespace + method)
        url = self.url.format(env=self.hosts[GSX_ENV], region=GSX_REGION)

        if method is "Authenticate":
            root.append(self.data)
        else:
            request_name = method + "Request"
            request = ET.SubElement(root, request_name)
            request.append(GSX_SESSION)

            if self._request == request_name:
                "Some requests don't have a top-level container."
                self.data = list(self.data)[0]

            request.append(self.data)

        data = ET.tostring(self.env, "UTF-8")
        logging.debug(data)

        parsed = urlparse(url)

        ws = httplib.HTTPSConnection(parsed.netloc)
        ws.putrequest("POST", parsed.path)
        ws.putheader("User-Agent", "py-gsxws 0.9")
        ws.putheader("Content-type", 'text/xml; charset="UTF-8"')
        ws.putheader("Content-length", "%d" % len(data))
        ws.putheader("SOAPAction", '"%s"' % method)
        ws.endheaders()
        ws.send(data)

        res = ws.getresponse()
        xml = res.read()

        if res.status > 200:
            raise GsxError(xml=xml)

        logging.debug("Response: %s %s %s" % (res.status, res.reason, xml))
        response = response or self._response

        for r in ET.fromstring(xml).findall("*//%s" % response):
            self.objects.append(GsxObject.from_xml(r))

        return self.objects

    def __str__(self):
        return ET.tostring(self.env)


class GsxObject(object):
    "XML/SOAP representation of a GSX object"
    _data = {}

    def __init__(self, *args, **kwargs):
        self._data = {}
        self._formats = get_formats()

        for a in args:
            k = validate(a)
            if k is not None:
                kwargs[k] = a

        for k, v in kwargs.items():
            self.__setattr__(k, v)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super(GsxObject, self).__setattr__(name, value)
            return

        if isinstance(value, int):
            value = str(value)
        if isinstance(value, date):
            value = value.strftime(self._formats['df'])
        if isinstance(value, time):
            value = value.strftime(self._formats['tf'])
        if isinstance(value, bool):
            value = 'Y' if value else 'N'
        if isinstance(value, date):
            value = value.strftime(self._formats['df'])

        self._data[name] = value

    def __getattr__(self, name):
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError("Invalid attribute: %s" % name)

    def _submit(self, arg, method, ret=None):
        self._req = GsxRequest(**{arg: self})
        result = self._req._submit(method, ret)
        return result if len(result) > 1 else result[0]

    def to_xml(self, root):
        "Returns this object as an XML element"
        root = ET.Element(root)
        for k, v in self._data.items():
            el = ET.SubElement(root, k)
            el.text = v

        return root

    @classmethod
    def from_xml(cls, el):
        obj = GsxObject()

        for r in el:
            newitem = cls.from_xml(r)
            k, v = r.tag, r.text

            if hasattr(obj, k):
                # found duplicate tag %s" % k
                attr = obj.__getattr__(k)
                if isinstance(attr, list):
                    # append to existing list
                    newattr = attr.append(newitem)
                    setattr(obj, k, newattr)
                else:
                    # convert to list
                    setattr(obj, k, [v, newitem])
            else:
                # unique tag %s -> set the dictionary" % k
                setattr(obj, k, newitem)

            if k in ["partsInfo"]:
                # found new list item %s" % k
                attr = []
                attr.append(GsxObject.from_xml(r))

                setattr(obj, k, attr)

            if k in ['packingList', 'proformaFileData', 'returnLabelFileData']:
                v = base64.b64decode(v)

            if isinstance(v, basestring):

                v = unicode(v)  # "must be unicode, not str"

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

                setattr(obj, k, v)

        return obj


class GsxSession(GsxObject):
    userId = ""
    password = ""
    languageCode = ""
    userTimeZone = ""
    serviceAccountNo = ""

    _cache = None
    _cache_key = ""
    _session_id = ""
    _namespace = "glob:"

    def __init__(self, user_id, password, sold_to, language, timezone):
        self.userId = user_id
        self.password = password
        self.languageCode = language
        self.userTimeZone = timezone
        self.serviceAccountNo = str(sold_to)

        md5 = hashlib.md5()
        md5.update(user_id + self.serviceAccountNo)

        self._cache_key = md5.hexdigest()
        self._cache = GsxCache(self._cache_key)

    def get_session(self):
        session = ET.Element("userSession")
        session_id = ET.Element("userSessionId")
        session_id.text = self._session_id
        session.append(session_id)
        return session

    def login(self):
        global GSX_SESSION

        if not self._cache.get() is None:
            GSX_SESSION = self._cache.get()
        else:
            #result = self._submit("AuthenticateRequest", "Authenticated")
            self._req = GsxRequest(AuthenticateRequest=self)
            result = self._req._submit("Authenticate")
            self._session_id = result[0].userSessionId
            GSX_SESSION = self.get_session()
            self._cache.set(GSX_SESSION)

        return GSX_SESSION

    def logout(self):
        return GsxRequest(LogoutRequest=self)


def connect(user_id, password, sold_to,
            environment='it',
            language='en',
            timezone='CEST',
            region='emea',
            locale='en_XXX'):
    """
    Establishes connection with GSX Web Services.
    Returns the session ID of the new connection.
    """
    global GSX_ENV
    global GSX_LANG
    global GSX_LOCALE
    global GSX_REGION

    GSX_LANG = language
    GSX_REGION = region
    GSX_LOCALE = locale
    GSX_ENV = environment

    act = GsxSession(user_id, password, sold_to, language, timezone)
    return act.login()


if __name__ == '__main__':
    import doctest
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
    logging.basicConfig(level=logging.DEBUG)
    connect(**vars(args))
    doctest.testmod()
