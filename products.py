import sys
from gsxws import connect, GsxError
from repairs import GsxObject
from lookups import Lookup

class GsxRequest(object):
    def submit(self, method, data, attr=None):
        """Submits the SOAP envelope
        """
        from gsxws import CLIENT, SESSION
        f = getattr(CLIENT.service, method)
        
        try:
            result = f(data)
            return getattr(result, attr) if attr else result
        except suds.WebFault, e:
            raise GsxError(fault=e)


class Product(GsxObject, GsxRequest):
    """Something serviceable that Apple makes
    """
    serialNumber = ""
    alternateDeviceId = ""
    configDescription = ""

    def model(self):
        """Returns the model description of this Product

        >>> Product(serialNumber='DGKFL06JDHJP').model().configDescription
        iMac (27-inch, Mid 2011)
        """
        dt = self._make_type("ns3:fetchProductModelRequestType")
        dt.productModelRequest = self.data
        result = self.submit('FetchProductModel', dt, "productModelResponse")[0]
        self.configDescription = result.configDescription
        self.productLine = result.productLine
        self.configCode = result.configCode
        return result

    def warranty(self):
        """The Warranty Status API retrieves the same warranty details
        displayed on the GSX Coverage screen.
        If part information is provided, the part warranty information is returned.
        If you do not provide the optional part information in the
        warranty status request, the unit level warranty information is returned.

        >>> Product(serialNumber='DGKFL06JDHJP').warranty().warrantyStatus
        Out Of Warranty (No Coverage)
        """
        dt = self._make_type("ns3:warrantyStatusRequestType")
        dt.unitDetail = self.data
        result = self.submit("WarrantyStatus", dt, "warrantyDetailInfo")
        return result

    @property
    def parts(self):
        pass

if __name__ == '__main__':
    import doctest
    connect(*sys.argv[1:4])
    doctest.testmod()
