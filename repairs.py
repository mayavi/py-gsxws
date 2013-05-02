"""
gsxws/repairs.py
"""
import sys
from gsxws import connect, SESSION


class GsxObject(object):
    data = dict()
    def __init__(self, **kwargs):
        self.data = kwargs


class Customer(GsxObject):
    """
    Customer address for GSX

    >>> Customer(adressLine1='blaa').data
    {'adressLine1': 'blaa'}
    """
    adressLine1 = ""
    city = ""
    country = ""
    firstName = ""
    lastName = ""
    primaryPhone = ""
    region = ""
    state = "ZZ"
    zipCode = ""
    emailAddress = ""
        

class RepairOrderLine(GsxObject):
    partNumber = ""
    partNumber = ""
    comptiaCode = ""
    comptiaModifier = ""


class Repair(GsxObject):
    """docstring for Repair"""
    customerAddress = None
    symptom = ""
    diagnosis = ""
    notes = ""
    purchaseOrderNumber = ""
    referenceNumber = ""
    requestReview = False
    serialNumber = ""
    unitReceivedDate = ""
    unitReceivedTime = ""

    orderLines = []

    def get_data(self):
        return {'repairData': self.data}

    def lookup(self):
        pass


class CarryInRepair(Repair):
    """
    GSX validates the information and if all of the validations go through,
    it obtains a quote for the repair and creates the carry-in repair

    >>> CarryInRepair(customerAddress=Customer(firstName='Filipp')).get_data()
    {}
    """
    shipTo = ""
    fileName = ""
    fileData = ""
    diagnosedByTechId = ""
        

class IndirectOnsiteRepair(Repair):
    """docstring for IndirectOnsiteRepair"""
    pass


if __name__ == '__main__':
    import doctest
    connect(*sys.argv[1:4])
    doctest.testmod()
