# -*- coding: utf-8 -*-

"""
https://gsxwsut.apple.com/apidocs/ut/html/WSAPIChangeLog.html?user=asp
"""
import urllib

from lookups import Lookup
from diagnostics import Diagnostics
from core import GsxObject, GsxError


def models():
    """
    >>> models() # doctest: +ELLIPSIS
    {'MAC_ACC': {'models': ['AirPort Card', ...
    """
    import os
    import yaml
    filepath = os.path.join(os.path.dirname(__file__), "products.yaml")
    return yaml.load(open(filepath, 'r'))


class Product(GsxObject):
    "Something serviceable made by Apple"
    _namespace = "glob:"

    def model(self):
        """
        Returns the model description of this Product

        >>> Product('DGKFL06JDHJP').model().configDescription
        u'iMac (27-inch, Mid 2011)'
        """
        result = self._submit("productModelRequest", "FetchProductModel")

        self.configDescription = result.configDescription
        self.productLine = result.productLine
        self.configCode = result.configCode
        return result

    def warranty(self, parts=None):
        """
        The Warranty Status API retrieves the same warranty details
        displayed on the GSX Coverage screen.
        If part information is provided, the part warranty information is returned.
        If you do not provide the optional part information in the
        warranty status request, the unit level warranty information is returned.

        >>> Product('DGKFL06JDHJP').warranty().warrantyStatus
        u'Out Of Warranty (No Coverage)'
        >>> Product('DGKFL06JDHJP').warranty().estimatedPurchaseDate
        datetime.date(2011, 6, 2)
        >>> Product('WQ8094DW0P1').warranty([(u'661-5070', u'Z26',)]) # doctest: +ELLIPSIS
        {'warrantyStatus': 'Out Of Warranty (No Coverage)',...
        """
        if hasattr(self, "alternateDeviceId"):
            if not self.serialNumber:
                self.activation()
        try:
            self.partNumbers = []
            for k, v in parts:
                part = GsxObject(partNumber=k, comptiaCode=v)
                self.partNumbers.append(part)
        except Exception:
            pass

        self._submit("unitDetail", "WarrantyStatus", "warrantyDetailInfo")
        self.warrantyDetails = self._req.objects
        return self.warrantyDetails

    def parts(self):
        """
        >>> Product('DGKFL06JDHJP').parts() # doctest: +ELLIPSIS
        {'exchangePrice': '0', 'isSerialized': 'N', 'partType': 'Other',...
        >>> Product(productName='MacBook Pro (17-inch, Mid 2009)').parts() # doctest: +ELLIPSIS
        {'exchangePrice': '0', 'isSerialized': 'N', 'partType': 'Other',...
        """
        try:
            return Lookup(serialNumber=self.serialNumber).parts()
        except AttributeError:
            return Lookup(productName=self.productName).parts()

    def repairs(self):
        """
        >>> Product(serialNumber='DGKFL06JDHJP').repairs() # doctest: +ELLIPSIS
        {'customerName': 'Lepalaan,Filipp',...
        """
        return Lookup(serialNumber=self.serialNumber).repairs()

    def diagnostics(self):
        """
        >>> Product('DGKFL06JDHJP').diagnostics()
        """
        diags = Diagnostics(serialNumber=self.serialNumber)
        return diags.fetch()

    def fetch_image(self):
        """
        >>> Product('DGKFL06JDHJP').fetch_image()
        """
        if not hasattr(self, "imageURL"):
            raise GsxError("No URL to fetch product image")

        try:
            result = urllib.urlretrieve(self.imageURL)
            return result[0]
        except Exception, e:
            raise GsxError("Failed to fetch product image: %s" % e)

    def activation(self):
        """
        The Fetch iOS Activation Details API is used to
        fetch activation details of iOS Devices.

        >>> Product('013348005376007').activation().unlocked
        True
        >>> Product('W874939YX92').activation().unlocked # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        GsxError: Provided serial number does not belong to an iOS Device...
        """
        self._namespace = "glob:"
        ad = self._submit("FetchIOSActivationDetailsRequest",
                          "FetchIOSActivationDetails",
                          "activationDetailsInfo")
        self.serialNumber = ad.serialNumber
        return ad


if __name__ == '__main__':
    import sys
    import doctest
    import logging
    from core import connect
    logging.basicConfig(level=logging.DEBUG)
    connect(*sys.argv[1:])
    doctest.testmod()
