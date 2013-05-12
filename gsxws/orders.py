class Order(GsxObject):
    def __init__(self, type='stocking', *args, **kwargs):
        super(Order, self).__init__(*args, **kwargs)
        self.data['orderLines'] = list()

    def add_part(self, part_number, quantity):
        self.data['orderLines'].append({
            'partNumber': part_number, 'quantity': quantity
        })

    def submit(self):
        dt = CLIENT.factory.create('ns1:createStockingOrderRequestType')
        dt.userSession = SESSION
        dt.orderData = self.data

        try:
            result = CLIENT.service.CreateStockingOrder(dt)
            return result.orderConfirmation
        except suds.WebFault, e:
            raise GsxError(fault=e)
