"""Demonstrate A, B, C on synthetic actors, bookings, URLs and mock effects."""
from marketguard import Marketplace
m=Marketplace()
m.register('hotel1',verified=True)
m.property('hotel1-property','hotel1',verified=True,evidence='independent-review-fixture')
m.booking('B001','hotel1-property','guest1','MERCHANT-1',50000,'EUR','https://pay.example.test/checkout')
print('SCENARIO A: fake property blocked')
m.property('fake-villa','hotel1',verified=False,evidence='')
try:
    m.authorize('hotel1','fake-villa','publish',{'listing_id':'FAKE','property':'fake-villa','version':'1','content':'fake villa'})
except Exception as exc:
    print('DENY:',exc)
print('SCENARIO A: legitimate property published')
listing={'listing_id':'L001','property':'hotel1-property','version':'v1','content':'Verified example accommodation'}
g=m.authorize('hotel1','hotel1-property','publish',listing)
print(m.effect(g,'listing_sink',listing))
print('SCENARIO B: legitimate login but unauthorised payment request')
try:
    m.authorize('hotel1','hotel1-property','message',{'booking':'B001','recipient':'guest1','text':'Send payment now','requests_payment':True,'merchant':'MERCHANT-1','payment_url':'https://phishing.example.test/pay'})
except Exception as exc:
    print('DENY:',exc)
print('SCENARIO C: beneficiary changed after authorisation')
payment={'booking':'B001','beneficiary':'MERCHANT-1','amount':50000,'currency':'EUR'}
g=m.authorize('hotel1','hotel1-property','payment',payment)
print(m.effect(g,'payment_sink',{**payment,'beneficiary':'ATTACKER-99'}))
print('After a failed sink check, the grant is burned:')
print(m.effect(g,'payment_sink',payment))
new_grant=m.authorize('hotel1','hotel1-property','payment',payment)
print('A NEW independently authorized grant can commit:',m.effect(new_grant,'payment_sink',payment))
print('Repeat after successful use:',m.effect(new_grant,'payment_sink',payment))
print('Audit integrity:',m.audit_valid(),'Mock effects:',m.effect_count())
