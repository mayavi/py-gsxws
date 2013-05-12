import urllib
import tempfile
from core import GsxObject, GsxError


class Part(GsxObject):
    def lookup(self):
        lookup = Lookup(**self.data)
        return lookup.parts()

    def fetch_image(self):
        """
        Tries the fetch the product image for this service part
        """
        if self.partNumber is None:
            raise GsxError("Cannot fetch part image without part number")

        image = '%s_350_350.gif' % self.partNumber
        url = 'https://km.support.apple.com.edgekey.net/kb/imageService.jsp?image=%s' % image
        tmpfile = tempfile.mkstemp(suffix=image)

        try:
            return urllib.urlretrieve(url, tmpfile[1])[0]
        except Exception, e:
            raise GsxError('Failed to fetch part image: %s' % e)


if __name__ == '__main__':
    import doctest
    from core import connect
    logging.basicConfig(level=logging.DEBUG)
    connect(*sys.argv[1:4])
    doctest.testmod()
