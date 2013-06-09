## {{{ http://code.activestate.com/recipes/573463/ (r7)

import re
import base64
import tempfile
from datetime import datetime
from xml.etree import ElementTree


class XmlDictObject(dict):
    """
    Adds object like functionality to the standard dictionary.
    """
    def __init__(self, initdict=None):
        if initdict is None:
            initdict = {}
        dict.__init__(self, initdict)

    def __getattr__(self, item):
        v = self.__getitem__(item)

        if item in ["packingList", "proformaFileData", "returnLabelFileData"]:
            v = base64.b64decode(v)
            of = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            of.write(v)
            return of.name

        try:
            if isinstance(v, basestring):
                v = unicode(v)  # "must be unicode, not str"

            # convert Y and N to boolean
            if re.search(r'^[YN]$', v):
                v = (v == "Y")

            # strip currency prefix and munge into float
            if re.search(r'Price$', item):
                v = float(re.sub(r'[A-Z ,]', '', v))

            # Convert timestamps to native Python type
            # 18-Jan-13 14:38:04
            if re.search(r'TimeStamp$', item):
                v = datetime.strptime(v, "%d-%b-%y %H:%M:%S")

            if re.search(r'Date$', item):
                # looks like some sort of date, let's try to convert
                try:
                    # standard GSX format: "mm/dd/yy"
                    dt = datetime.strptime(v, "%m/%d/%y")
                    v = dt.date()
                except ValueError:
                    pass

                try:
                    # some dates are formatted as "yyyy-mm-dd"
                    dt = datetime.strptime(v, "%Y-%m-%d")
                    v = dt.date()
                except (ValueError, TypeError):
                    pass
        except TypeError:
            pass

        return v

    def __setattr__(self, item, value):
        self.__setitem__(item, value)

    def __str__(self):
        if self.has_key('_text'):
            return self.__getitem__('_text')
        else:
            return ''

    @staticmethod
    def Wrap(x):
        """
        Static method to wrap a dictionary recursively as an XmlDictObject
        """

        if isinstance(x, dict):
            return XmlDictObject((k, XmlDictObject.Wrap(v)) for (k, v) in x.iteritems())
        elif isinstance(x, list):
            return [XmlDictObject.Wrap(v) for v in x]
        else:
            return x

    @staticmethod
    def _UnWrap(x):
        if isinstance(x, dict):
            return dict((k, XmlDictObject._UnWrap(v)) for (k, v) in x.iteritems())
        elif isinstance(x, list):
            return [XmlDictObject._UnWrap(v) for v in x]
        else:
            return x

    def UnWrap(self):
        """
        Recursively converts an XmlDictObject to a standard dictionary and returns the result.
        """

        return XmlDictObject._UnWrap(self)


def _ConvertDictToXmlRecurse(parent, dictitem):
    assert type(dictitem) is not type([])

    if isinstance(dictitem, dict):
        for (tag, child) in dictitem.iteritems():
            if str(tag) == '_text':
                parent.text = str(child)
            elif type(child) is type([]):
                # iterate through the array and convert
                for listchild in child:
                    elem = ElementTree.Element(tag)
                    parent.append(elem)
                    _ConvertDictToXmlRecurse(elem, listchild)
            else:                
                elem = ElementTree.Element(tag)
                parent.append(elem)
                _ConvertDictToXmlRecurse(elem, child)
    else:
        parent.text = str(dictitem)


def ConvertDictToXml(xmldict):
    """
    Converts a dictionary to an XML ElementTree Element
    """
    roottag = xmldict.keys()[0]
    root = ElementTree.Element(roottag)
    _ConvertDictToXmlRecurse(root, xmldict[roottag])
    return root


def _ConvertXmlToDictRecurse(node, dictclass):
    nodedict = dictclass()

    if len(node.items()) > 0:
        # if we have attributes, set them
        nodedict.update(dict(node.items()))

    for child in node:
        # recursively add the element's children
        newitem = _ConvertXmlToDictRecurse(child, dictclass)
        if nodedict.has_key(child.tag):
            # found duplicate tag, force a list
            if type(nodedict[child.tag]) is type([]):
                # append to existing list
                nodedict[child.tag].append(newitem)
            else:
                # convert to list
                nodedict[child.tag] = [nodedict[child.tag], newitem]
        else:
            # only one, directly set the dictionary
            nodedict[child.tag] = newitem

    if node.text is None:
        text = ''
    else:
        text = node.text.strip()

    if len(nodedict) > 0:
        # if we have a dictionary add the text as a dictionary value (if there is any)
        if len(text) > 0:
            nodedict['_text'] = text
    else:
        # if we don't have child nodes or attributes, just set the text
        nodedict = text

    return nodedict


def ConvertXmlToDict(root, dictclass=XmlDictObject):
    """
    Converts an XML file or ElementTree Element to a dictionary
    """
    # If a string is passed in, try to open it as a file
    if type(root) == type(''):
        root = ElementTree.parse(root).getroot()
    elif not isinstance(root, ElementTree.Element):
        raise TypeError("Expected ElementTree.Element or file path string")

    return dictclass({root.tag: _ConvertXmlToDictRecurse(root, dictclass)})
