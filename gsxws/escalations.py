# -*- coding: utf-8 -*-

from core import GsxObject


class Escalation(GsxObject):
    def create(self):
        """
        The Create General Escalation API allows users to create
        a general escalation in GSX. The API was earlier known as GSX Help.
        """
        dt = self._make_type("ns1:createGenEscRequestType")
        dt.escalationRequest = self.data
        return self.submit("CreateGeneralEscalation", dt, "escalationConfirmation")

    def update(self):
        """
        The Update General Escalation API allows Depot users to
        update a general escalation in GSX.
        """
        dt = self._make_type("ns1:updateGeneralEscRequestType")
        dt.escalationRequest = self.data
        return self.submit("UpdateGeneralEscalation", dt, "escalationConfirmation")
