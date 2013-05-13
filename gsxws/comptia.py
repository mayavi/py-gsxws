import os
import json

from core import GsxObject, GsxError, GsxCache

MODIFIERS = (
    ("A", "Not Applicable"),
    ("B", "Continuous"),
    ("C", "Intermittent"),
    ("D", "Fails After Warm Up"),
    ("E", "Environmental"),
    ("F", "Configuration: Peripheral"),
    ("G", "Damaged"),
)

GROUPS = (
    ('0', "General"),
    ('1', "Visual"),
    ('2', "Displays"),
    ('3', "Mass Storage"),
    ('4', "Input Devices"),
    ('5', "Boards"),
    ('6', "Power"),
    ('7', "Printer"),
    ('8', "Multi-function Device"),
    ('9', "Communication Devices"),
    ('A', "Share"),
    ('B', "iPhone"),
    ('E', "iPod"),
    ('F', "iPad"),
)


class CompTIA(GsxObject):
    "Stores and accesses CompTIA codes."
    def __init__(self):
        """
        Initialize CompTIA symptoms from JSON file
        """
        df = open(os.path.join(os.path.dirname(__file__), 'comptia.json'))
        self._data = json.load(df)

    def fetch(self):
        """
        The CompTIA Codes Lookup API retrieves a list of CompTIA groups and modifiers.

        Here we must resort to raw XML parsing since SUDS throws this:
        suds.TypeNotFound: Type not found: 'comptiaDescription'
        when calling CompTIACodes()...

        >>> CompTIA().fetch()
        {'A': {'972': 'iPod not recognized',...
        """
        global COMPTIA_CACHE
        if COMPTIA_CACHE.get("comptia"):
            return COMPTIA_CACHE.get("comptia")

        CLIENT.set_options(retxml=True)
        dt = CLIENT.factory.create("ns3:comptiaCodeLookupRequestType")
        dt.userSession = SESSION

        try:
            xml = CLIENT.service.CompTIACodes(dt)
        except suds.WebFault, e:
            raise GsxError(fault=e)

        root = ET.fromstring(xml).findall('.//%s' % 'comptiaInfo')[0]

        for el in root.findall(".//comptiaGroup"):
            group = {}
            comp_id = el[0].text

            for ci in el.findall('comptiaCodeInfo'):
                group[ci[0].text] = ci[1].text

            self.data[comp_id] = group

        COMPTIA_CACHE.put("comptia", self.data)
        return self.data

    def symptoms(self, component=None):
        """
        Returns all known CompTIA symptom codes or just the ones
        belonging to the given component code.
        """
        r = dict()

        for g, codes in self.data.items():
            r[g] = list()
            for k, v in codes.items():
                r[g].append((k, v,))

        return r[component] if component else r
