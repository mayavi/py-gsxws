# -*- coding: utf-8 -*-

from core import GsxObject


class Diagnostics(GsxObject):
    _namespace = "glob:"

    def fetch(self):
        """
        The Fetch Repair Diagnostics API allows the service providers/depot/carriers
        to fetch MRI/CPU diagnostic details from the Apple Diagnostic Repository OR
        diagnostic test details of iOS Devices.
        The ticket is generated within GSX system.

        >>> Diagnostics(diagnosticEventNumber='12942008007242012052919').fetch()
        """
        if hasattr(self, "alternateDeviceId"):
            self._submit("lookupRequestData", "FetchIOSDiagnostic", "diagnosticTestData")
        else:
            self._submit("lookupRequestData", "FetchRepairDiagnostic", "FetchRepairDiagnosticResponse")

        return self._req.objects

    def events(self):
        """
        The Fetch Diagnostic Event Numbers API allows users to retrieve all
        diagnostic event numbers associated with provided input
        (serial number or alternate device ID).
        """
        self._submit("lookupRequestData", "FetchDiagnosticEventNumbers", "diagnosticEventNumbers")
        return self._req.objects
