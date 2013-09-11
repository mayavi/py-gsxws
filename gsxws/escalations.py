# -*- coding: utf-8 -*-

import os.path
from core import GsxObject
from lookups import Lookup

STATUS_OPEN = 'O'
STATUS_CLOSED = 'C'
STATUS_ESCALATED = 'E'

STATUSES = (
    (STATUS_OPEN, 'Open'),
    (STATUS_CLOSED, 'Closed'),
    (STATUS_ESCALATED, 'Escalated'),
)

CONTEXTS = (
    'Serial Number',
    'Alternate Device Id',
    'Dispatch Id',
    'SRO Number',
    'Invoice Number',
    'Order Number',
    'SSO number',
    'Part Number',
    'EEE Code',
    'Tracking Number',
    'Module Serial Number',
    'Escalation Id',
)

ISSUE_TYPES = (
    ('AMQ', 'Account Management Question'),
    ('UQ', 'GSX Usage Question'),
    ('OSI', 'Order Status Issue'),
    ('PRI', 'Part Return Issue'),
    ('PPOR', 'Problem Placing Order/Repair'),
    ('PUR', 'Problem Updating Repair'),
    ('SCI', 'Shipping Carrier Issue'),
    ('SES', 'Service Excellence Scoring'),
    ('ARF', 'Apple Retail Feedback'),
    ('DF', 'Depot Feedback'),
    ('FS', 'GSX Feedback/Suggestion'),
    ('WS', 'GSX Web Services (API)'),
    ('SEPI', 'Service Excellence Program Information'),
    ('TTI', 'Technical or Troubleshooting Issue'),
    ('DTA', 'Diagnostic Tool Assistance'),
    ('BIQ', 'Billing or Invoice Question'),
    ('SESC', 'Safety Issue'),
)


class FileAttachment(GsxObject):
    def __init__(self, fp):
        super(FileAttachment, self).__init__()
        self.fileName = os.path.basename(fp)
        self.fileData = open(fp, 'r')


class Escalation(GsxObject):
    _namespace = 'asp:'

    def create(self):
        """
        The Create General Escalation API allows users to create
        a general escalation in GSX. The API was earlier known as GSX Help.
        """
        return self._submit("escalationRequest", "CreateGeneralEscalation",
                            "escalationConfirmation")

    def update(self):
        """
        The Update General Escalation API allows Depot users to
        update a general escalation in GSX.
        """
        return self._submit("escalationRequest", "UpdateGeneralEscalation",
                            "escalationConfirmation")

    def lookup(self):
        """
        The General Escalation Details Lookup API allows to fetch details
        of a general escalation created by AASP or a carrier.
        """
        return Lookup(escalationId=self.escalationId).lookup("GeneralEscalationDetailsLookup")
