# -*- coding: utf-8 -*-

import sys
import base64
import logging
import tempfile
from datetime import date

from core import GsxObject

class Lookup(GsxObject):
    def __init__(self, *args, **kwargs):
        super(Lookup, self).__init__(*args, **kwargs)
        self._namespace = "asp:"

    def lookup(self, method, response="lookupResponseData"):
        return self._submit("lookupRequestData", method, response)

    def parts(self):
        """
        The Parts Lookup API allows users to access part and part pricing data prior to
        creating a repair or order. Parts lookup is also a good way to search for
        part numbers by various attributes of a part
        (config code, EEE code, serial number, etc.).
        """
        self._namespace = "core:"
        return self.lookup("PartsLookup", "parts")

    def repairs(self):
        """
        The Repair Lookup API mimics the front-end repair search functionality.
        It fetches up to 2500 repairs in a given criteria.
        Subsequently, the extended Repair Status API can be used
        to retrieve more details of the repair.
        """
        return self.lookup("RepairLookup")

    def invoices(self):
        """
        The Invoice ID Lookup API allows AASP users
        to fetch the invoice generated for last 24 hrs

        >>> Lookup(shipTo=677592, invoiceDate=date(2012,2,6)).invoices().invoiceID
        '9670348809'
        """
        return self.lookup("InvoiceIDLookup")

    def invoice_details(self):
        """
        The Invoice Details Lookup API allows AASP users to
        download invoice for a given invoice id.
        >>> Lookup(invoiceID=9670348809).invoice_details()
        """
        result = self.lookup("InvoiceDetailsLookup")
        pdf = base64.b64decode(result.invoiceData)
        outfile = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        outfile.write(pdf)
        result.invoiceData = outfile.name
        return result

if __name__ == '__main__':
    import sys
    import doctest
    logging.basicConfig(level=logging.DEBUG)
    connect(*sys.argv[1:4])
    doctest.testmod()
