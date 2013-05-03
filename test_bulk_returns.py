import json
import gsxws
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.client').setLevel(logging.DEBUG)

sold_to = ''
gsxws.connect(user_id='', password='', sold_to=sold_to, environment='ut')

rep = gsxws.Repair(dispatchId='')
#rep.update_sn({'partNumber':'661-5465', 'serialNumber': 'VM020ZLD5RU', 'oldSerialNumber': 'W80320QAAGZ'})
rep.mark_complete()
df = open('/Users/filipp/Projects/py-gsxws/tests/parts_register_return.json')
data = json.loads(df.read())
data['shipToCode'] = sold_to

print data
ret = gsxws.Returns(**data)
print ret.register_parts()
