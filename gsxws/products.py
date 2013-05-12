"""
https://gsxwsut.apple.com/apidocs/ut/html/WSAPIChangeLog.html?user=asp
"""

import sys
import urllib

import logging
from lookups import Lookup
from diagnostics import Diagnostics
from core import GsxObject, GsxError


class Product(GsxObject):
    "Something serviceable made by Apple"
    _namespace = "glob:"

    def model(self):
        """
        Returns the model description of this Product

        >>> Product(serialNumber='DGKFL06JDHJP').model().configDescription
        'iMac (27-inch, Mid 2011)'
        """
        result = self._submit("productModelRequest", "FetchProductModel")

        self.configDescription = result.configDescription
        self.productLine = result.productLine
        self.configCode = result.configCode
        return result

    def warranty(self):
        """
        The Warranty Status API retrieves the same warranty details
        displayed on the GSX Coverage screen.
        If part information is provided, the part warranty information is returned.
        If you do not provide the optional part information in the
        warranty status request, the unit level warranty information is returned.

        >>> Product('DGKFL06JDHJP').warranty().warrantyStatus
        'Out Of Warranty (No Coverage)'
        """
        self._submit("unitDetail", "WarrantyStatus", "warrantyDetailInfo")
        self.warrantyDetails = self._req.objects[0]
        return self.warrantyDetails

    def parts(self):
        """
        >>> Product('DGKFL06JDHJP').parts() # doctest: +ELLIPSIS
        [<core.GsxObject object at ...
        """
        return Lookup(serialNumber=self.serialNumber).parts()

    def repairs(self):
        """
        >>> Product(serialNumber='DGKFL06JDHJP').repairs() # doctest: +ELLIPSIS
        <core.GsxObject object at ...
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
        >>> Product('DGKFL06JDHJP').warranty().fetch_image()
        """
        if not hasattr(self, "imageURL"):
            raise GsxError("No URL to fetch product image")

        try:
            result = urllib.urlretrieve(self.imageURL)
            return result[0]
        except Exception, e:
            raise GsxError("Failed to fetch product image: %s" % e)

    def get_activation(self):
        """
        The Fetch iOS Activation Details API is used to
        fetch activation details of iOS Devices.

        >>> Product('013348005376007').get_activation().unlocked
        'true'
        >>> Product('W874939YX92').get_activation().unlocked # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        GsxError: Provided serial number does not belong to an iOS Device...
        """
        self._namespace = "glob:"
        act = self._submit("FetchIOSActivationDetailsRequest", "FetchIOSActivationDetails")
        return act


if __name__ == '__main__':
    import doctest
    from core import connect
    logging.basicConfig(level=logging.DEBUG)
    connect(*sys.argv[1:4])
    doctest.testmod()
