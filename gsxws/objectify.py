# -*- coding: utf-8 -*-

import os
import re
import base64
import tempfile

from lxml import objectify, etree
from lxml.objectify import StringElement

from datetime import datetime

BASE64_TYPES = ('packingList', 'proformaFileData', 'returnLabelFileData',)
FLOAT_TYPES = ('totalFromOrder', 'exchangePrice', 'stockPrice', 'netPrice',)
BOOLEAN_TYPES = ('isSerialized', 'popMandatory', 'limitedWarranty', 'partCovered', 'acPlusFlag',)
DATETIME_TYPES = ('dispatchSentDate',)

TZMAP = {
    'GMT': '',        # Greenwich Mean Time
    'PDT': '-0700',   # Pacific Daylight Time
    'PST': '-0800',   # Pacific Standard Time
    'CDT': '-0700',   # Central Daylight Time
    'CST': '-0600',   # Central Standard Time
    'EST': '-0500',   # Eastern Standard Time
    'EDT': '-0400',   # Eastern Daylight Time
    'CET': '+0100',   # Central European Time
    'CEST': '+0200',  # Central European Summer Time
    'IST': '+0530',   # Indian Standard Time
    'CCT': '+0800',   # Chinese Coast Time
    'JST': '+0900',   # Japan Standard Time
    'ACST': '+0930',  # Austrailian Central Standard Time
    'AEST': '+1000',  # Australian Eastern Standard Time
    'ACDT': '+1030',  # Australian Central Daylight Time
    'AEDT': '+1100',  # Australian Eastern Daylight Time
    'NZST': '+1200',  # New Zealand Standard Time
}


class GsxElement(StringElement):
    def __unicode__(self):
        return self.pyval

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __repr__(self):
        return str(self.text)


class GsxDateElement(GsxElement):
    @property
    def pyval(self):
        try:
            # standard GSX format: "mm/dd/yy"
            return datetime.strptime(self.text, "%m/%d/%y").date()
        except ValueError:
            pass

        try:
            # some dates are formatted as "yyyy-mm-dd"
            return datetime.strptime(self.text, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass

    def __repr__(self):
        return str(datetime.strftime(self.pyval, '%Y-%m-%d'))


class GsxBooleanElement(GsxElement):
    @property
    def pyval(self):
        return self.text == 'Y'


class GsxPriceElement(GsxElement):
    @property
    def pyval(self):
        return float(re.sub(r'[A-Z ,]', '', self.text))


class GsxAttachment(GsxElement):
    @property
    def pyval(self):
        v = base64.b64decode(self.text)
        of = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        of.write(v)
        return of.name


class GsxDatetimeElement(GsxElement):
    @property
    def pyval(self):
        # 2011-01-27 11:45:01 PST
        # Unfortunately we have to chomp off the TZ info...
        m = re.search(r'^(\d+\-\d+\-\d+ \d+:\d+:\d+) (\w+)$', self.text)
        ts, tz = m.groups()
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")


class GsxTimestampElement(GsxElement):
    @property
    def pyval(self):
        return datetime.strptime(self.text, "%d-%b-%y %H:%M:%S")


class GsxClassLookup(etree.CustomElementClassLookup):
    def lookup(self, node_type, document, namespace, name):
        if name in DATETIME_TYPES:
            return GsxDatetimeElement
        if name in BOOLEAN_TYPES:
            return GsxBooleanElement
        if name in BASE64_TYPES:
            return GsxAttachment
        if name in FLOAT_TYPES:
            return GsxPriceElement
        if re.search(r'Date$', name):
            return GsxDateElement

        return objectify.ObjectifiedElement


def parse(root, response):
    parser = objectify.makeparser(remove_blank_text=True)
    parser.set_element_class_lookup(GsxClassLookup())

    if isinstance(root, basestring) and os.path.exists(root):
        root = objectify.parse(root, parser)
    else:
        root = objectify.fromstring(root, parser)

    return root.find('*//%s' % response)

if __name__ == '__main__':
    import doctest
    import logging
    logging.basicConfig(level=logging.DEBUG)
    doctest.testmod()
