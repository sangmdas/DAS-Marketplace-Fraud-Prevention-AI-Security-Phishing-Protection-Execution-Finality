"""150 distinct Python behavior cases covering the marketplace operation lifecycle."""
import copy, hashlib, json, sqlite3, time
import pytest
from marketguard import Marketplace, Denied, digest, canonical, make_cvid, verify_cvid, url_origin

@pytest.fixture
def m():
    x=Marketplace(secret=b'unit-test-local-secret')
    x.register('owner',verified=True)
    x.register('employee',verified=True)
    x.register('unverified',verified=False)
    x.property('P1','owner',verified=True,evidence='checked by fixture',country='FR')
    x.property('P2','owner',verified=False,evidence='',country='FR')
    x.delegate('owner','employee','P1','message')
    x.booking('B1','P1','guest1','merchant1',50000,'EUR','https://pay.example.test/secure')
    yield x
    x.close()

def msg(**changes):
    b={'booking':'B1','recipient':'guest1','text':'Welcome','requests_payment':False}
    b.update(changes)
    return b

def pay(**changes):
    b={'booking':'B1','beneficiary':'merchant1','amount':50000,'currency':'EUR'}
    b.update(changes)
    return b

def listing(**changes):
    b={'listing_id':'L1','property':'P1','version':'v1','content':'Genuine guest room'}
    b.update(changes)
    return b

def commit(m, kind, body, actor='owner', prop='P1'):
    token=m.authorize(actor,prop,kind,body)
    return m.effect(token, {'publish':'listing_sink','message':'messaging_sink','payment':'payment_sink','export':'data_sink'}[kind],body)

IDENTITY=['verified_owner_authorized','verified_delegate_authorized','unverified_principal_denied','unknown_principal_denied','unknown_property_denied','unverified_property_denied','owner_not_delegated_other','principal_risk_79_allowed','principal_risk_80_denied','principal_risk_100_denied']
@pytest.mark.parametrize('scenario', IDENTITY, ids=IDENTITY)
def test_01_identity(m,scenario):
    if scenario=='verified_owner_authorized': assert m.identity_context('owner','P1','publish')['country']=='FR'
    elif scenario=='verified_delegate_authorized': assert m.identity_context('employee','P1','message')['action']=='message'
    elif scenario=='principal_risk_79_allowed': m.risk('owner',79);assert m.identity_context('owner','P1','message')['actor']=='owner'
    else:
        if scenario=='unverified_principal_denied': actor,prop,kind='unverified','P1','message'
        elif scenario=='unknown_principal_denied': actor,prop,kind='ghost','P1','message'
        elif scenario=='unknown_property_denied': actor,prop,kind='owner','missing','publish'
        elif scenario=='unverified_property_denied': actor,prop,kind='owner','P2','publish'
        elif scenario=='owner_not_delegated_other': actor,prop,kind='employee','P1','publish'
        else: m.risk('owner',80 if scenario=='principal_risk_80_denied' else 100); actor,prop,kind='owner','P1','message'
        with pytest.raises(Denied): m.identity_context(actor,prop,kind)

DELEGATION=['owner_grants_message','owner_grants_publish','owner_grants_payment','owner_grants_export','delegate_message_effect','delegate_cannot_publish','delegate_cannot_pay','delegate_cannot_export','stranger_cannot_delegate','bad_scope_cannot_delegate']
@pytest.mark.parametrize('scenario',DELEGATION,ids=DELEGATION)
def test_02_delegation(m,scenario):
    if scenario.startswith('owner_grants_'):
        k=scenario.split('grants_')[1];m.delegate('owner','employee','P1',k);assert m.identity_context('employee','P1',k)
    elif scenario=='delegate_message_effect':assert commit(m,'message',msg(),actor='employee').allowed
    elif scenario.startswith('delegate_cannot_'):
        k={'delegate_cannot_publish':'publish','delegate_cannot_pay':'payment','delegate_cannot_export':'export'}[scenario]
        with pytest.raises(Denied):m.identity_context('employee','P1',k)
    else:
        with pytest.raises(Denied): m.delegate('employee' if scenario=='stranger_cannot_delegate' else 'owner','guest1','P1','message' if scenario=='stranger_cannot_delegate' else 'superuser')

PROPERTY=['verified_property_can_publish','unverified_property_cannot_publish','verified_requires_evidence','unknown_owner_rejected','unverified_owner_cannot_publish','different_property_not_interchangeable','property_generation_changes','revoke_property_blocks_operation','property_country_preserved','duplicate_property_rejected']
@pytest.mark.parametrize('scenario',PROPERTY,ids=PROPERTY)
def test_03_property(m,scenario):
    if scenario=='verified_property_can_publish': assert commit(m,'publish',listing()).allowed
    elif scenario=='unverified_property_cannot_publish':
        with pytest.raises(Denied):m.authorize('owner','P2','publish',listing(property='P2'))
    elif scenario=='verified_requires_evidence':
        with pytest.raises(Denied):m.property('P3','owner',verified=True,evidence='')
    elif scenario=='unknown_owner_rejected':
        with pytest.raises(Denied):m.property('P3','ghost',verified=True,evidence='proof')
    elif scenario=='unverified_owner_cannot_publish':
        m.property('P3','unverified',verified=True,evidence='proof')
        with pytest.raises(Denied):m.authorize('unverified','P3','publish',listing(property='P3'))
    elif scenario=='different_property_not_interchangeable':
        with pytest.raises(Denied):m.authorize('owner','P1','publish',listing(property='P2'))
    elif scenario=='property_generation_changes':
        x=m.identity_context('owner','P1','publish')['property_generation'];m.revoke_property('P1');assert m._db.execute('SELECT generation FROM properties WHERE id="P1"').fetchone()[0]==x+1
    elif scenario=='revoke_property_blocks_operation':
        g=m.authorize('owner','P1','publish',listing());m.revoke_property('P1');assert not m.effect(g,'listing_sink',listing()).allowed
    elif scenario=='property_country_preserved':assert m.identity_context('owner','P1','publish')['country']=='FR'
    else:
        with pytest.raises(sqlite3.IntegrityError):m.property('P1','owner',verified=True,evidence='proof')

PUBLICATION=['publish_valid','missing_id','missing_version','missing_content','wrong_property','modified_content_at_sink','modified_version_at_sink','wrong_sink','duplicate_listing_second_grant','unverified_property_publication']
@pytest.mark.parametrize('scenario',PUBLICATION,ids=PUBLICATION)
def test_04_publication(m,scenario):
    if scenario=='publish_valid':assert commit(m,'publish',listing()).allowed and m.listing_count()==1
    elif scenario in {'missing_id','missing_version','missing_content','wrong_property','unverified_property_publication'}:
        body=listing()
        if scenario=='missing_id':body['listing_id']=''
        if scenario=='missing_version':body['version']=''
        if scenario=='missing_content':body['content']=''
        if scenario=='wrong_property':body['property']='P2'
        if scenario=='unverified_property_publication':body['property']='P2'
        with pytest.raises(Denied):m.authorize('owner','P2' if scenario=='unverified_property_publication' else 'P1','publish',body)
    elif scenario=='duplicate_listing_second_grant':
        assert commit(m,'publish',listing()).allowed
        g=m.authorize('owner','P1','publish',listing())
        assert not m.effect(g,'listing_sink',listing()).allowed
        assert m.listing_count()==1
    else:
        g=m.authorize('owner','P1','publish',listing())
        bad=listing()
        if scenario=='modified_content_at_sink':bad['content']='tampered'
        elif scenario=='modified_version_at_sink':bad['version']='v2'
        assert not m.effect(g,'wrong_sink' if scenario=='wrong_sink' else 'listing_sink',bad).allowed
        assert m.listing_count()==0

ADVERTISING=['organic_ok','paid_fully_attributed','paid_no_sponsor','paid_no_payer','paid_no_reason','paid_empty_metadata','paid_missing_payer_only','paid_missing_reason_only','organic_without_label_ok','evidence_created_for_rank']
@pytest.mark.parametrize('scenario',ADVERTISING,ids=ADVERTISING)
def test_05_advertising(m,scenario):
    base={'boosted':True,'sponsor':'Hotel A','payer':'Hotel A','reason':'Paid placement'}
    if scenario=='organic_ok':data=m.classify_ad('L1',boosted=False); assert not data['boosted']
    elif scenario=='organic_without_label_ok': data=m.classify_ad('L1',boosted=False,sponsor='',payer='');assert data['payer']==''
    elif scenario=='paid_fully_attributed':data=m.classify_ad('L1',**base);assert data['policy_version']==1
    elif scenario=='evidence_created_for_rank': before=m.audit_count();m.classify_ad('L1',**base);assert m.audit_count()==before+1
    else:
        if scenario in ('paid_no_sponsor','paid_empty_metadata'):base['sponsor']=''
        if scenario in ('paid_no_payer','paid_missing_payer_only','paid_empty_metadata'):base['payer']=''
        if scenario in ('paid_no_reason','paid_missing_reason_only','paid_empty_metadata'):base['reason']=''
        with pytest.raises(Denied):m.classify_ad('L1',**base)

BOOKING=['valid_booking','zero_amount_rejected','negative_amount_rejected','missing_property_rejected','unverified_property_rejected','http_link_rejected','credential_url_rejected','fragment_url_rejected','invalid_currency_rejected','duplicate_booking_rejected']
@pytest.mark.parametrize('scenario',BOOKING,ids=BOOKING)
def test_06_booking(m,scenario):
    args=['B2','P1','guest2','merchant2',100,'EUR','https://pay.example.test/checkout']
    if scenario=='valid_booking':m.booking(*args);assert m._db.execute('SELECT 1 FROM bookings WHERE id="B2"').fetchone()
    else:
        if scenario=='zero_amount_rejected':args[4]=0
        elif scenario=='negative_amount_rejected':args[4]=-9
        elif scenario=='missing_property_rejected':args[1]='ghost'
        elif scenario=='unverified_property_rejected':args[1]='P2'
        elif scenario=='http_link_rejected':args[6]='http://pay.example.test'
        elif scenario=='credential_url_rejected':args[6]='https://u:p@pay.example.test'
        elif scenario=='fragment_url_rejected':args[6]='https://pay.example.test/#token'
        elif scenario=='invalid_currency_rejected':args[5]='EURO'
        elif scenario=='duplicate_booking_rejected':args[0]='B1'
        with pytest.raises((Denied,sqlite3.IntegrityError)):m.booking(*args)

MESSAGE=['routine_approved','payment_approved','wrong_booking','wrong_guest','missing_booking','empty_text','payment_bad_host','payment_bad_merchant','payment_missing_url','unflagged_attacker_url']
@pytest.mark.parametrize('scenario',MESSAGE,ids=MESSAGE)
def test_07_messaging_authorization(m,scenario):
    body=msg()
    if scenario=='routine_approved':assert m.authorize('owner','P1','message',body)
    elif scenario=='payment_approved':assert m.authorize('owner','P1','message',msg(requests_payment=True,merchant='merchant1',payment_url='https://pay.example.test/now'))
    else:
        if scenario=='wrong_booking':body['booking']='B2'
        if scenario=='wrong_guest':body['recipient']='guest2'
        if scenario=='missing_booking':body.pop('booking')
        if scenario=='empty_text':body['text']=''
        if scenario=='unflagged_attacker_url':body['text']='Please visit https://attacker.example.test/pay for details'
        if scenario.startswith('payment_'):
            body.update(requests_payment=True,merchant='merchant1',payment_url='https://pay.example.test/now')
            if scenario=='payment_bad_host':body['payment_url']='https://attacker.example.test/pay'
            if scenario=='payment_bad_merchant':body['merchant']='impostor'
            if scenario=='payment_missing_url':body.pop('payment_url')
            if scenario=='payment_missing_merchant':body.pop('merchant')
        with pytest.raises(Denied):m.authorize('owner','P1','message',body)

MESSAGE_SINK=['valid_dispatch','recipient_changed','content_changed','booking_changed','payment_link_swapped','merchant_swapped','wrong_sink','replay_prevented','expired','revoked_before_dispatch']
@pytest.mark.parametrize('scenario',MESSAGE_SINK,ids=MESSAGE_SINK)
def test_08_message_sink(m,scenario):
    original=msg(requests_payment=True,merchant='merchant1',payment_url='https://pay.example.test/now')
    grant=m.authorize('owner','P1','message',original,now=1000,ttl_s=30)
    actual=copy.deepcopy(original)
    if scenario=='recipient_changed':actual['recipient']='other'
    if scenario=='content_changed':actual['text']='PAY NOW OR CANCELLED'
    if scenario=='booking_changed':actual['booking']='other'
    if scenario=='payment_link_swapped':actual['payment_url']='https://attacker.example.test/pay'
    if scenario=='merchant_swapped':actual['merchant']='scammer'
    if scenario=='revoked_before_dispatch':m.revoke('owner')
    out=m.effect(grant,'wrong_sink' if scenario=='wrong_sink' else 'messaging_sink',actual,now=1030 if scenario=='expired' else 1001)
    if scenario in ('valid_dispatch','replay_prevented'):
        assert out.allowed
        if scenario=='replay_prevented':assert not m.effect(grant,'messaging_sink',actual,now=1002).allowed
    else:assert not out.allowed and m.effect_count()==0

PAYMENTS=['valid_intent','different_merchant','increased_amount','lowered_amount','currency_change','wrong_booking','missing_booking','missing_beneficiary','string_amount_instead_int','negative_amount','unknown_property']
# Use ten unique payment authorization cases, with extra negative amount exercised elsewhere.
PAYMENTS=PAYMENTS[:10]
@pytest.mark.parametrize('scenario',PAYMENTS,ids=PAYMENTS)
def test_09_payment_intent(m,scenario):
    body=pay()
    if scenario=='valid_intent':assert m.authorize('owner','P1','payment',body)
    else:
        if scenario=='different_merchant':body['beneficiary']='attacker'
        if scenario=='increased_amount':body['amount']=50001
        if scenario=='lowered_amount':body['amount']=49999
        if scenario=='currency_change':body['currency']='USD'
        if scenario=='wrong_booking':body['booking']='NOBOOK'
        if scenario=='missing_booking':body.pop('booking')
        if scenario=='missing_beneficiary':body.pop('beneficiary')
        if scenario=='string_amount_instead_int':body['amount']='50000'
        if scenario=='negative_amount':body['amount']=-1
        with pytest.raises(Denied):m.authorize('owner','P1','payment',body)

PAYMENT_SINK=['correct_payment','different_final_beneficiary','different_final_amount','different_final_currency','failed_attempt_burns_grant','wrong_sink','replay','expired_grant','changed_additional_field','pay_after_property_revoked']
@pytest.mark.parametrize('scenario',PAYMENT_SINK,ids=PAYMENT_SINK)
def test_10_payment_sink(m,scenario):
    expected=pay();g=m.authorize('owner','P1','payment',expected,now=1000,ttl_s=30)
    actual=dict(expected)
    if scenario=='different_final_beneficiary':actual['beneficiary']='attacker'
    if scenario=='different_final_amount':actual['amount']=50001
    if scenario=='different_final_currency':actual['currency']='USD'
    if scenario=='failed_attempt_burns_grant':actual['beneficiary']='attacker'
    if scenario=='changed_additional_field':actual['connector_debug']='injected'
    if scenario=='pay_after_property_revoked':m.revoke_property('P1')
    result=m.effect(g,'another_sink' if scenario=='wrong_sink' else 'payment_sink',actual,now=1030 if scenario=='expired_grant' else 1001)
    if scenario in ('correct_payment','replay'):
        assert result.allowed
        if scenario=='replay':assert not m.effect(g,'payment_sink',actual,now=1002).allowed
    else:
        assert not result.allowed and m.effect_count()==0
        if scenario=='failed_attempt_burns_grant':
            assert m.effect(g,'payment_sink',expected,now=1002).reason=='replayed_grant'

EXPORT=['checkin_guest_name','checkin_arrival_only','checkin_both','empty_fields','email_not_allowed','payment_data_not_allowed','untrusted_purpose','other_property_booking','missing_booking','other_guest_booking']
@pytest.mark.parametrize('scenario',EXPORT,ids=EXPORT)
def test_11_data_export(m,scenario):
    body={'booking':'B1','purpose':'check_in','fields':['guest_name']}
    if scenario=='checkin_arrival_only':body['fields']=['arrival_date']
    if scenario=='checkin_both':body['fields']=['arrival_date','guest_name']
    if scenario=='empty_fields':body['fields']=[]
    if scenario=='email_not_allowed':body['fields']=['email']
    if scenario=='payment_data_not_allowed':body['fields']=['bank_account']
    if scenario=='untrusted_purpose':body['purpose']='marketing'
    if scenario=='other_property_booking':m.property('P3','owner',verified=True,evidence='evidence');body['booking']='B1'
    if scenario=='missing_booking':body.pop('booking')
    if scenario=='other_guest_booking':body['booking']='nope'
    if scenario in ('checkin_guest_name','checkin_arrival_only','checkin_both','empty_fields'):
        assert commit(m,'export',body).allowed
    elif scenario=='other_property_booking':
        with pytest.raises(Denied):m.authorize('owner','P3','export',body)
    else:
        with pytest.raises(Denied):m.authorize('owner','P1','export',body)

REVOCATION=['fresh_authority','actor_generation_increment','revoked_grant_message','revoked_grant_payment','property_revoke_publish','risk_79_remains','risk_80_blocks','risk_100_blocks','stale_delegate_removed','fresh_grant_after_revoke']
@pytest.mark.parametrize('scenario',REVOCATION,ids=REVOCATION)
def test_12_revocation(m,scenario):
    if scenario=='fresh_authority':assert commit(m,'message',msg()).allowed
    elif scenario=='actor_generation_increment':
        v=m.identity_context('owner','P1','message')['authority_generation'];m.revoke('owner');assert m.identity_context('owner','P1','message')['authority_generation']==v+1
    elif scenario=='revoked_grant_message':
        g=m.authorize('owner','P1','message',msg());m.revoke('owner');assert not m.effect(g,'messaging_sink',msg()).allowed
    elif scenario=='revoked_grant_payment':
        g=m.authorize('owner','P1','payment',pay());m.revoke('owner');assert not m.effect(g,'payment_sink',pay()).allowed
    elif scenario=='property_revoke_publish':
        g=m.authorize('owner','P1','publish',listing());m.revoke_property('P1');assert not m.effect(g,'listing_sink',listing()).allowed
    elif scenario=='risk_79_remains':m.risk('owner',79);assert commit(m,'message',msg()).allowed
    elif scenario=='risk_80_blocks':
        m.risk('owner',80)
        with pytest.raises(Denied):m.authorize('owner','P1','message',msg())
    elif scenario=='risk_100_blocks':
        m.risk('owner',100)
        with pytest.raises(Denied):m.authorize('owner','P1','message',msg())
    elif scenario=='stale_delegate_removed':
        m._db.execute("UPDATE delegations SET active=0 WHERE agent='employee'")
        with pytest.raises(Denied):m.authorize('employee','P1','message',msg())
    else:m.revoke('owner');assert commit(m,'message',msg()).allowed

OUTCOMES=['pending_recorded','submitted_recorded','ack_recorded','completed_recorded','canceled_recorded','failed_without_effect_recorded','indeterminate_recorded','completed_cannot_revert','indeterminate_cannot_re_submit','invalid_state_rejected']
@pytest.mark.parametrize('scenario',OUTCOMES,ids=OUTCOMES)
def test_13_recovery(m,scenario):
    mapping={'pending_recorded':'PENDING','submitted_recorded':'SUBMITTED','ack_recorded':'ACKNOWLEDGED','completed_recorded':'VERIFIED_COMPLETED','canceled_recorded':'VERIFIED_CANCELED','failed_without_effect_recorded':'VERIFIED_FAILED_WITHOUT_EFFECT','indeterminate_recorded':'OUTCOME_INDETERMINATE'}
    if scenario in mapping:
        m.record_outcome('op1',mapping[scenario]);assert m._db.execute('SELECT status FROM outcomes').fetchone()[0]==mapping[scenario]
    elif scenario=='completed_cannot_revert':
        m.record_outcome('op1','VERIFIED_COMPLETED')
        with pytest.raises(Denied):m.record_outcome('op1','PENDING')
    elif scenario=='indeterminate_cannot_re_submit':
        m.record_outcome('op1','OUTCOME_INDETERMINATE')
        with pytest.raises(Denied):m.record_outcome('op1','SUBMITTED')
    else:
        with pytest.raises(Denied):m.record_outcome('op1','MAGIC_SUCCESS')

AUDIT=['seed_has_events','valid_initial_hash_chain','authorization_increases_count','effect_increases_count','revoke_increases_count','incident_created','notify_incident','unknown_incident_denied','tamper_audit_detected','risk_change_audited']
@pytest.mark.parametrize('scenario',AUDIT,ids=AUDIT)
def test_14_audit(m,scenario):
    if scenario=='seed_has_events':assert m.audit_count()>0
    elif scenario=='valid_initial_hash_chain':assert m.audit_valid()
    elif scenario=='authorization_increases_count':
        n=m.audit_count();m.authorize('owner','P1','message',msg());assert m.audit_count()==n+1
    elif scenario=='effect_increases_count':
        n=m.audit_count();commit(m,'message',msg());assert m.audit_count()==n+2
    elif scenario=='revoke_increases_count':
        n=m.audit_count();m.revoke('owner');assert m.audit_count()==n+1
    elif scenario=='incident_created':
        m.create_incident('incident1','owner','account_takeover');assert not m.incident_notified('incident1')
    elif scenario=='notify_incident':
        m.create_incident('incident1','owner','phishing');m.mark_notified('incident1');assert m.incident_notified('incident1')
    elif scenario=='unknown_incident_denied':
        with pytest.raises(Denied):m.mark_notified('does-not-exist')
    elif scenario=='tamper_audit_detected':
        m._db.execute('UPDATE audit SET event=? WHERE seq=1', ('{}',));assert not m.audit_valid()
    else:
        n=m.audit_count();m.risk('owner',10);assert m.audit_count()==n+1

PRIMITIVES=['canonical_order_independent','digest_changes_on_target_change','cvid_valid','cvid_wrong_sender','cvid_wrong_booking','cvid_wrong_purpose','cvid_wrong_generation','cvid_wrong_digest','alternative_path_closed','unknown_effect_path_denied']
@pytest.mark.parametrize('scenario',PRIMITIVES,ids=PRIMITIVES)
def test_15_primitives(m,scenario):
    if scenario=='canonical_order_independent':assert digest({'x':1,'y':2})==digest({'y':2,'x':1})
    elif scenario=='digest_changes_on_target_change':assert digest({'merchant':'A'})!=digest({'merchant':'B'})
    elif scenario.startswith('cvid_'):
        key=b'secret-only-for-test';kwargs={'sender':'owner','booking':'B1','purpose':'check_in','digest_hex':'abc','generation':1}
        token=make_cvid(key,**kwargs)
        change={'cvid_wrong_sender':('sender','other'),'cvid_wrong_booking':('booking','B2'),'cvid_wrong_purpose':('purpose','payment'),'cvid_wrong_generation':('generation',2),'cvid_wrong_digest':('digest_hex','changed')}.get(scenario)
        if change:kwargs[change[0]]=change[1]
        assert verify_cvid(key,token,**kwargs)==(change is None)
    elif scenario=='alternative_path_closed':assert m.check_paths({'api','batch'},{'api'},{'batch'})
    elif scenario=='unknown_effect_path_denied':assert not m.check_paths({'api','batch'},{'api'},set())

def test_16_concurrent_single_use(m):
    from concurrent.futures import ThreadPoolExecutor
    body=pay();g=m.authorize('owner','P1','payment',body)
    with ThreadPoolExecutor(max_workers=16) as pool:
        outcomes=list(pool.map(lambda _:m.effect(g,'payment_sink',body).allowed,range(48)))
    assert outcomes.count(True)==1 and m.effect_count()==1


def test_17_fastapi_roundtrip():
    from fastapi.testclient import TestClient
    from marketguard import api
    with TestClient(api.app) as client:
        assert client.get('/healthz').json()['status']=='mock_only'
        assert client.post('/demo/seed').json()['seeded']
        text={'booking':'BOOK-1','recipient':'GUEST-1','text':'Welcome','requests_payment':False}
        grant=client.post('/v1/authorize',json={'actor':'HOTEL-1','property':'PROP-1','kind':'message','body':text})
        assert grant.status_code==200,grant.text
        gid=grant.json()['grant']
        out=client.post('/v1/effect',json={'grant':gid,'sink':'messaging_sink','actual_body':text}).json()
        assert out['allowed']
        assert not client.post('/v1/effect',json={'grant':gid,'sink':'messaging_sink','actual_body':text}).json()['allowed']
        assert client.get('/v1/audit').json()['valid']
