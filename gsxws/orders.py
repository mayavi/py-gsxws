from core import GsxObject


class OrderLine(GsxObject):
    partNumber = None
    quantity = None


class APPOrder(GsxObject):
    pass


class StockingOrder(GsxObject):
    """
    Description:
    The Create Stocking Order API is used to create a stocking order.
    The purchase order number, ship-to number of the service provider
    and a list of parts are required.
    The service account number is obtained from the session.
    Quote is obtained for the parts and if it is processed successfully,
    a confirmation number, array of parts, sub-total, tax and total price are returned.
    The part details also contain the net price and availability.

    Context:
    The API can be invoked only after valid authentication.
    Authentication generates a session ID that needs to be passed while using this API.

    >>> StockingOrder(purchaseOrderNumber=111, shipToCode=677592).add_part('661-5097', 1).submit()
    """
    _namespace = "asp:"

    def __init__(self, *args, **kwargs):
        super(StockingOrder, self).__init__(*args, **kwargs)
        self.orderLines = list()

    def add_part(self, part_number, quantity):
        self.orderLines.append(OrderLine(partNumber=part_number, quantity=quantity))
        return self

    def submit(self):
        self._submit("orderData", "CreateStockingOrder", "orderConfirmation")
        return self._req.objects[0]


if __name__ == '__main__':
    import sys
    import doctest
    import logging
    from core import connect
    logging.basicConfig(level=logging.DEBUG)
    connect(*sys.argv[1:5])
    doctest.testmod()
