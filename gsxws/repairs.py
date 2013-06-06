"gsxws/repairs.py"
import re
import sys
import logging

from core import GsxObject, validate
from lookups import Lookup

REPAIR_TYPES = (
    ('CA', "Carry-In/Non-Replinished"),
    ('NE', "Return Before Replace"),
    ('NT', "No Trouble Found"),
    ('ON', "Onsite (Indirect/Direct)"),
    ('RR', "Repair Or Replace/Whole Unit Mail-In"),
    ('WH', "Mail-In"),
)


class Customer(GsxObject):
    """
    Customer address for GSX

    >>> Customer(adressLine1='blaa')._data
    {'adressLine1': 'blaa'}
    """
    city = ""
    region = ""
    country = ""
    state = "ZZ"
    zipCode = ""
    lastName = ""
    firstName = ""
    adressLine1 = ""
    emailAddress = ""
    primaryPhone = ""


class RepairOrderLine(GsxObject):
    partNumber = ""
    comptiaCode = ""
    comptiaModifier = ""


class ServicePart(GsxObject):
    "A generic service part (for PartInfo and whatnot)"
    def __init__(self, number, *args, **kwargs):
        super(ServicePart, self).__init__(*args, **kwargs)

        if not validate(number, "partNumber"):
            raise ValueError("Invalid part number: %s" % number)

        self.partNumber = number


class Repair(GsxObject):
    "Base class for the different GSX Repair types"
    _namespace = "asp:"

    def __init__(self, number=None, **kwargs):
        super(Repair, self).__init__(**kwargs)

        if number is not None:
            self.dispatchId = number

    def update_sn(self, parts):
        """
        Description
        The Update Serial Number API allows the service providers to update
        the module serial numbers.

        Context:
        The API is not applicable for whole unit replacement
        serial number entry (see KGB serial update).

        >>> Repair('G135762375').update_sn(ServicePart('661-4964', oldSerialNumber='W882300FK22YA'))
        """
        self.partInfo = parts
        if hasattr(self, "dispatchId"):
            self.repairConfirmationNumber = self.dispatchId

        self._submit("repairData", "UpdateSerialNumber", "repairConfirmation")
        return self._req.objects[0]

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
        self.serialNumber = sn
        self.repairConfirmationNumber = self.dispatchId

        self._submit("UpdateKGBSerialNumberRequest", "UpdateKGBSerialNumber",
                     "UpdateKGBSerialNumberResponse")

        return self._req.objects[0]

    def lookup(self):
        """
        Description:
        The Repair Lookup API mimics the front-end repair search functionality.
        It fetches up to 2500 repairs in a given criteria.
        Subsequently, the extended Repair Status API can be used
        to retrieve more details of the repair.

        >>> Repair(repairStatus='Open').lookup() #doctest: +ELLIPSIS
        [<core.GsxObject object at ...
        """
        self._namespace = "core:"
        return Lookup(**self._data).repairs()

    def delete(self):
        """
        The Delete Repair API allows the service providers to delete
        the existing GSX Initiated Carry-In, Return Before Replace & Onsite repairs
        which are in Declined-Rejected By TSPS Approver state,
        that do not have an active repair id.
        """
        pass

    def mark_complete(self, numbers=None):
        """
        The Mark Repair Complete API allows a single or an array of
        repair confirmation numbers to be submitted to GSX to be marked as complete.
        """
        self.repairConfirmationNumbers = numbers or self.dispatchId
        self._submit("MarkRepairCompleteRequest", "MarkRepairComplete",
                     "MarkRepairCompleteResponse")
        return self._req.objects[0]

    def status(self, numbers=None):
        """
        The Repair Status API retrieves the status
        for the submitted repair confirmation number(s).

        >>> Repair('G135773004').status().repairStatus
        u'Closed and Completed'
        """
        self.repairConfirmationNumbers = self.dispatchId
        status = self._submit("RepairStatusRequest", "RepairStatus", "repairStatus")[0]
        self.repairStatus = status.repairStatus
        self._status = status
        return status

    def details(self):
        """
        The Repair Details API includes the shipment information
        similar to the Repair Lookup API.

        >>> Repair('G135773004').details() #doctest: +ELLIPSIS
        <core.GsxObject object at ...
        """
        self._namespace = "core:"
        details = self._submit("RepairDetailsRequest", "RepairDetails", "lookupResponseData")

        # fix tracking URL if available
        for i, p in enumerate(details.partsInfo):
            try:
                url = re.sub('<<TRKNO>>', p.deliveryTrackingNumber, p.carrierURL)
                details.partsInfo[i].carrierURL = url
            except AttributeError:
                pass

        self.details = details
        return details


class CannotDuplicateRepair(Repair):
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


class CarryInRepair(Repair):
    """
    GSX validates the information and if all of the validations go through,
    it obtains a quote for the repair and creates the carry-in repair

    >>> CarryInRepair(requestReviewByApple=True).requestReviewByApple
    'Y'
    """

    _namespace = "emea:"

    def create(self):
        """
        GSX validates the information and if all of the validations go through,
        it obtains a quote for the repair and creates the carry-in repair.
        """
        return self._submit("repairData", "CreateCarryIn", "repairConfirmation")

    def update(self, newdata):
        """
        Description
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
        self._namespace = "asp:"
        # Merge old and new data (old data should have Dispatch ID)
        self._data.update(newdata)
        return self._submit("repairData", "UpdateCarryIn", "repairConfirmation")


class IndirectOnsiteRepair(Repair):
    """
    The Create Indirect Onsite Repair API is designed to create the indirect onsite repairs.
    When a service provider travels to the customer location to perform repair
    on a unit eligible for onsite service, they create an indirect repair.
    Once the repair is submitted, it is assigned a confirmation number,
    which is a reference number to identify the repair.
    """

    _namespace = "asp:"

    def create(self):
        if getattr(self, "shipTo"):  # Carry-In and OnSite use different field names!
            self.shippingLocation = self.shipTo
            del(self._data['shipTo'])

        if getattr(self, "poNumber"):
            self.purchaseOrderNumber = self.poNumber
            del(self._data['poNumber'])

        if getattr(self, "diagnosedByTechId"):
            self.technicianName = self.diagnosedByTechId
            del(self._data['diagnosedByTechId'])

        return self._submit("repairData", "CreateIndirectOnsiteRepair",
                            "repairConfirmation")


if __name__ == '__main__':
    import doctest
    from core import connect
    logging.basicConfig(level=logging.DEBUG)
    connect(*sys.argv[1:])
    doctest.testmod()
