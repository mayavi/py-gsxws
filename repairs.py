"""
gsxws/repairs.py
"""
import sys
from gsxws import connect


class GsxObject(object):

    data = {}

    def __init__(self, **kwargs):
        self.data = kwargs

    def _make_type(self, new_dt):
        """
        Creates the top-level datatype for the API call
        """
        from gsxws import CLIENT, SESSION
        dt = CLIENT.factory.create(new_dt)

        if SESSION:
            dt.userSession = SESSION

        return dt


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
    """
    Abstract base class for the different GSX Repair types
    """
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

    TYPES = (
        ('CA', "Carry-In/Non-Replinished"),
        ('NE', "Return Before Replace"),
        ('NT', "No Trouble Found"),
        ('ON', "Onsite (Indirect/Direct)"),
        ('RR', "Repair Or Replace/Whole Unit Mail-In"),
        ('WH', "Mail-In"),
    )

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
    """
    The Create Indirect Onsite Repair API is designed to create the indirect onsite repairs.
    When a service provider travels to the customer location to perform repair
    on a unit eligible for onsite service, they create an indirect repair.
    Once the repair is submitted, it is assigned a confirmation number,
    which is a reference number to identify the repair.
    """
    pass


if __name__ == '__main__':
    import doctest
    connect(*sys.argv[1:4])
    doctest.testmod()
