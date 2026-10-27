"""DAS marketplace fraud-prevention research simulator.

No external payments, messages or real property verifications are performed. The
SQLite event/effect registries stand in for protected resource interfaces.
"""
from __future__ import annotations
import hashlib, hmac, json, secrets, sqlite3, threading, time, re
from urllib.parse import urlsplit
from dataclasses import dataclass
from typing import Any


class Denied(Exception):
    """A governed operation cannot become effective."""


def canonical(data: dict[str, Any]) -> str:
    if not isinstance(data, dict):
        raise Denied('descriptor_not_object')
    try:
        return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    except (ValueError, TypeError, OverflowError) as exc:
        raise Denied('invalid_descriptor') from exc


def digest(data: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(data).encode('utf-8')).hexdigest()


def url_origin(url: str) -> str:
    try:
        p = urlsplit(url)
        if (p.scheme != 'https' or not p.hostname or p.username or p.password
                or p.fragment or p.port not in (None, 443)):
            raise Denied('invalid_payment_url')
        return p.hostname.lower().rstrip('.')
    except ValueError as exc:
        raise Denied('invalid_payment_url') from exc


SCHEMA = '''
CREATE TABLE principals(id TEXT PRIMARY KEY, verified INTEGER NOT NULL, generation INTEGER NOT NULL DEFAULT 1, risk INTEGER NOT NULL DEFAULT 0);
CREATE TABLE properties(id TEXT PRIMARY KEY, owner TEXT NOT NULL, verified INTEGER NOT NULL, evidence TEXT NOT NULL, country TEXT NOT NULL, generation INTEGER NOT NULL DEFAULT 1);
CREATE TABLE delegations(agent TEXT NOT NULL, property TEXT NOT NULL, action TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(agent,property,action));
CREATE TABLE bookings(id TEXT PRIMARY KEY, property TEXT NOT NULL, guest TEXT NOT NULL, merchant TEXT NOT NULL, amount INTEGER NOT NULL, currency TEXT NOT NULL, payment_host TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE grants(id TEXT PRIMARY KEY, principal TEXT NOT NULL, property TEXT NOT NULL, kind TEXT NOT NULL, sink TEXT NOT NULL, bodyhash TEXT NOT NULL, generation INTEGER NOT NULL, property_generation INTEGER NOT NULL, expires REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0);
CREATE TABLE effects(id TEXT PRIMARY KEY, grant TEXT NOT NULL UNIQUE, kind TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE listings(id TEXT PRIMARY KEY, property TEXT NOT NULL, version TEXT NOT NULL, contenthash TEXT NOT NULL);
CREATE TABLE risk_events(id TEXT PRIMARY KEY, principal TEXT NOT NULL, category TEXT NOT NULL, handled INTEGER NOT NULL DEFAULT 0);
CREATE TABLE audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, entry_hash TEXT NOT NULL);
CREATE TABLE outcomes(id TEXT PRIMARY KEY, status TEXT NOT NULL, processor_ref TEXT);
'''

VALID_SINKS = {'publish': 'listing_sink', 'message': 'messaging_sink', 'payment': 'payment_sink', 'export': 'data_sink'}

@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    operation_id: str | None = None


class Marketplace:
    """Single-process mock protected store, suitable for deterministic tests only.

    It assumes clients cannot access this SQLite connection directly and the sink
    identity is authenticated by a trusted host (not by a caller-controlled header).
    """
    def __init__(self, path: str = ':memory:', *, secret: bytes | None = None):
        self._db = sqlite3.connect(path, isolation_level=None, check_same_thread=False, timeout=5)
        self._db.executescript(SCHEMA)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._secret = secret if secret is not None else secrets.token_bytes(32)

    def close(self):
        self._db.close()

    def _audit(self, event: dict):
        body = canonical(event)
        last = self._db.execute('SELECT entry_hash FROM audit ORDER BY seq DESC LIMIT 1').fetchone()
        prev = last['entry_hash'] if last else '0'*64
        h = hashlib.sha256((prev + body).encode()).hexdigest()
        self._db.execute('INSERT INTO audit(event,entry_hash) VALUES (?,?)', (body, h))

    def audit_valid(self):
        prev = '0'*64
        for r in self._db.execute('SELECT event,entry_hash FROM audit ORDER BY seq'):
            if hashlib.sha256((prev + r['event']).encode()).hexdigest() != r['entry_hash']:
                return False
            prev = r['entry_hash']
        return True

    def audit_count(self):
        return self._db.execute('SELECT COUNT(*) FROM audit').fetchone()[0]

    def register(self, actor: str, *, verified: bool):
        with self._lock:
            self._db.execute('INSERT INTO principals(id,verified) VALUES (?,?)', (actor, int(verified)))
            self._audit({'type': 'kybc', 'principal': actor, 'verified': verified})

    def property(self, ident: str, owner: str, *, verified: bool, evidence: str, country: str='EU'):
        with self._lock:
            if not self._db.execute('SELECT 1 FROM principals WHERE id=?',(owner,)).fetchone():
                raise Denied('unknown_operator')
            if verified and not evidence:
                raise Denied('missing_real_world_evidence')
            self._db.execute('INSERT INTO properties(id,owner,verified,evidence,country) VALUES (?,?,?,?,?)', (ident,owner,int(verified),evidence,country))
            self._audit({'type': 'property_registration', 'id': ident, 'verified': verified})

    def delegate(self, owner: str, agent: str, property_id: str, action: str):
        with self._lock:
            p = self._db.execute('SELECT owner FROM properties WHERE id=?',(property_id,)).fetchone()
            if not p or p['owner'] != owner or action not in VALID_SINKS:
                raise Denied('delegation_unauthorized')
            self._db.execute('INSERT OR REPLACE INTO delegations(agent,property,action,active) VALUES (?,?,?,1)',(agent,property_id,action))
            self._audit({'type': 'delegate', 'owner': owner, 'agent': agent, 'scope': action})

    def booking(self, ident: str, property_id: str, guest: str, merchant: str, amount: int, currency: str, payment_url: str):
        if amount <= 0 or len(currency)!=3:
            raise Denied('invalid_booking_terms')
        host = url_origin(payment_url)
        with self._lock:
            p=self._db.execute('SELECT verified FROM properties WHERE id=?',(property_id,)).fetchone()
            if not p or not p['verified']:
                raise Denied('unverified_property')
            self._db.execute('INSERT INTO bookings(id,property,guest,merchant,amount,currency,payment_host) VALUES (?,?,?,?,?,?,?)', (ident,property_id,guest,merchant,amount,currency.upper(),host))
            self._audit({'type': 'booking', 'id': ident, 'property': property_id})

    def risk(self, actor: str, level: int):
        with self._lock:
            self._db.execute('UPDATE principals SET risk=? WHERE id=?',(level,actor))
            self._audit({'type': 'risk_change', 'actor': actor, 'level': level})

    def revoke(self, actor: str):
        with self._lock:
            self._db.execute('UPDATE principals SET generation=generation+1 WHERE id=?',(actor,))
            self._audit({'type': 'revoke', 'actor': actor})

    def revoke_property(self, property_id: str):
        with self._lock:
            self._db.execute('UPDATE properties SET generation=generation+1, verified=0 WHERE id=?',(property_id,))
            self._audit({'type': 'revoke_property', 'property': property_id})

    def identity_context(self, actor: str, property_id: str, action: str) -> dict:
        p = self._db.execute('SELECT * FROM principals WHERE id=?',(actor,)).fetchone()
        prop = self._db.execute('SELECT * FROM properties WHERE id=?',(property_id,)).fetchone()
        if not p or not p['verified'] or p['risk'] >= 80:
            raise Denied('operator_not_current')
        if not prop or not prop['verified'] or not prop['evidence']:
            raise Denied('property_not_verified')
        delegation = self._db.execute('SELECT active FROM delegations WHERE agent=? AND property=? AND action=?',(actor,property_id,action)).fetchone()
        if prop['owner'] != actor and not (delegation and delegation['active']):
            raise Denied('operation_outside_delegation')
        return {'actor':actor,'property':property_id,'action':action,'country':prop['country'],'authority_generation':p['generation'],'property_generation':prop['generation']}

    def validate_body(self, kind: str, property_id: str, body: dict):
        if kind == 'publish':
            if not all(isinstance(body.get(k),str) and body[k] for k in ('listing_id','version','content')):
                raise Denied('incomplete_listing')
            if body.get('property') != property_id:
                raise Denied('listing_property_mismatch')
        elif kind == 'message':
            b=self._db.execute('SELECT * FROM bookings WHERE id=?',(body.get('booking'),)).fetchone()
            if not b or not b['active'] or b['property']!=property_id or b['guest'] != body.get('recipient'):
                raise Denied('message_booking_mismatch')
            if not isinstance(body.get('text'), str) or not body['text']:
                raise Denied('empty_message')
            # Independently inspect obvious web links in final content rather than
            # trusting a caller-supplied requests_payment classification alone.
            # This is NOT a complete anti-phishing classifier or redirect resolver.
            for candidate in re.findall(r'https?://[^\s<>\"\']+', body['text'], flags=re.IGNORECASE):
                if url_origin(candidate) != b['payment_host']:
                    raise Denied('unapproved_message_link')
            if body.get('requests_payment',False):
                if not body.get('payment_url') or url_origin(body['payment_url']) != b['payment_host']:
                    raise Denied('unauthorized_payment_destination')
                if body.get('merchant') != b['merchant']:
                    raise Denied('unauthorized_message_merchant')
        elif kind == 'payment':
            b=self._db.execute('SELECT * FROM bookings WHERE id=?',(body.get('booking'),)).fetchone()
            if not b or not b['active'] or b['property'] != property_id:
                raise Denied('payment_booking_mismatch')
            if (body.get('beneficiary') != b['merchant'] or body.get('amount') != b['amount'] or body.get('currency') != b['currency']):
                raise Denied('unauthorized_payment_terms')
        elif kind == 'export':
            b=self._db.execute('SELECT * FROM bookings WHERE id=?',(body.get('booking'),)).fetchone()
            if not b or b['property']!=property_id or body.get('purpose')!='check_in' or set(body.get('fields',[]))-{'guest_name','arrival_date'}:
                raise Denied('export_outside_purpose')
        else:
            raise Denied('unknown_operation_type')

    def authorize(self, actor: str, property_id: str, kind: str, body: dict, *, ttl_s: int=60, now: float|None=None) -> str:
        if kind not in VALID_SINKS or ttl_s <= 0 or ttl_s>3600:
            raise Denied('invalid_scope_or_ttl')
        now = time.time() if now is None else now
        with self._lock:
            ctx=self.identity_context(actor,property_id,kind)
            self.validate_body(kind,property_id,body)
            gid=secrets.token_hex(16)
            self._db.execute('INSERT INTO grants(id,principal,property,kind,sink,bodyhash,generation,property_generation,expires) VALUES (?,?,?,?,?,?,?,?,?)', (gid,actor,property_id,kind,VALID_SINKS[kind],digest(body),ctx['authority_generation'],ctx['property_generation'],now+ttl_s))
            self._audit({'type':'authorize','kind':kind,'actor':actor,'grant':gid,'digest':digest(body)})
            return gid

    def effect(self, grant: str, sink: str, actual_body: dict, *, now: float|None=None) -> Decision:
        now = time.time() if now is None else now
        with self._lock:
            self._db.execute('BEGIN IMMEDIATE')
            try:
                row=self._db.execute('SELECT * FROM grants WHERE id=?',(grant,)).fetchone()
                if not row:
                    raise Denied('unknown_grant')
                if row['used']:
                    raise Denied('replayed_grant')
                if row['sink'] != sink:
                    raise Denied('wrong_sink')
                if now>=row['expires']:
                    raise Denied('expired_grant')
                ctx=self.identity_context(row['principal'],row['property'],row['kind'])
                if (ctx['authority_generation']!=row['generation'] or ctx['property_generation']!=row['property_generation']):
                    raise Denied('revoked_generation')
                self.validate_body(row['kind'],row['property'],actual_body)
                if not hmac.compare_digest(row['bodyhash'],digest(actual_body)):
                    raise Denied('actual_operation_mismatch')
                cursor=self._db.execute('UPDATE grants SET used=1 WHERE id=? AND used=0',(grant,))
                if cursor.rowcount!=1:
                    raise Denied('raced_grant')
                op=secrets.token_hex(12)
                self._db.execute('INSERT INTO effects(id,grant,kind,body,status) VALUES (?,?,?,?,?)',(op,grant,row['kind'],canonical(actual_body),'MOCK_COMMITTED'))
                if row['kind']=='publish':
                    self._db.execute('INSERT INTO listings(id,property,version,contenthash) VALUES (?,?,?,?)',(actual_body['listing_id'],row['property'],actual_body['version'],hashlib.sha256(actual_body['content'].encode()).hexdigest()))
                self._audit({'type':'effect','operation':op,'grant':grant,'sink':sink,'kind':row['kind']})
                self._db.execute('COMMIT')
                return Decision(True,'mock_effect_committed',op)
            except (Denied,sqlite3.IntegrityError) as exc:
                self._db.execute('ROLLBACK')
                # Conservative one-shot model: a failed sink verification burns
                # an otherwise active grant. Real deployments MUST authenticate
                # the sink caller to prevent malicious grant-ID denial-of-service.
                if 'row' in locals() and row is not None and not row['used']:
                    self._db.execute('BEGIN IMMEDIATE')
                    try:
                        self._db.execute('UPDATE grants SET used=1 WHERE id=? AND used=0', (grant,))
                        self._audit({'type':'denied_and_burned','grant':grant,'reason':str(exc)})
                        self._db.execute('COMMIT')
                    except Exception:
                        self._db.execute('ROLLBACK')
                        raise
                return Decision(False, str(exc) if isinstance(exc,Denied) else 'resource_constraint_failed')
            except Exception:
                self._db.execute('ROLLBACK')
                raise

    def listing_count(self):
        return self._db.execute('SELECT COUNT(*) FROM listings').fetchone()[0]

    def effect_count(self):
        return self._db.execute('SELECT COUNT(*) FROM effects').fetchone()[0]

    def record_outcome(self, op: str, status: str, processor_ref: str|None=None):
        permitted={'PENDING','SUBMITTED','ACKNOWLEDGED','VERIFIED_COMPLETED','VERIFIED_CANCELED','VERIFIED_FAILED_WITHOUT_EFFECT','OUTCOME_INDETERMINATE'}
        if status not in permitted:
            raise Denied('invalid_outcome')
        with self._lock:
            prior=self._db.execute('SELECT status FROM outcomes WHERE id=?',(op,)).fetchone()
            if prior and prior['status']=='VERIFIED_COMPLETED' and status!='VERIFIED_COMPLETED':
                raise Denied('cannot_undo_completed')
            if prior and prior['status']=='OUTCOME_INDETERMINATE' and status=='SUBMITTED':
                raise Denied('no_blind_retry')
            self._db.execute('INSERT INTO outcomes(id,status,processor_ref) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,processor_ref=excluded.processor_ref',(op,status,processor_ref))
            self._audit({'type':'outcome','operation':op,'status':status})

    def create_incident(self, ref: str, actor: str, category: str):
        with self._lock:
            self._db.execute('INSERT INTO risk_events(id,principal,category) VALUES (?,?,?)',(ref,actor,category))
            self._audit({'type':'incident','ref':ref,'category':category})

    def mark_notified(self, ref: str):
        with self._lock:
            cur=self._db.execute('UPDATE risk_events SET handled=1 WHERE id=?',(ref,))
            if not cur.rowcount: raise Denied('unknown_incident')
            self._audit({'type':'notified','ref':ref})

    def incident_notified(self, ref: str):
        row=self._db.execute('SELECT handled FROM risk_events WHERE id=?',(ref,)).fetchone()
        return bool(row and row['handled'])

    def classify_ad(self, listing: str, *, boosted:bool, sponsor:str='',payer:str='',reason:str='') -> dict:
        if boosted and not all([sponsor,payer,reason]):
            raise Denied('missing_advertising_metadata')
        data={'listing':listing,'boosted':boosted,'sponsor':sponsor,'payer':payer,'reason':reason,'policy_version':1}
        self._audit({'type':'rank_classification','listing':listing,'boosted':boosted})
        return data

    def check_paths(self, required: set[str], controlled: set[str], disabled: set[str]) -> bool:
        if not required:
            return False  # unknown graph coverage never proves closure
        return required <= (controlled | disabled)


def make_cvid(secret: bytes, *, sender: str, booking: str, purpose: str, digest_hex: str, generation:int) -> str:
    data={'sender':sender,'booking':booking,'purpose':purpose,'digest':digest_hex,'generation':generation}
    return hmac.new(secret,canonical(data).encode(),hashlib.sha256).hexdigest()


def verify_cvid(secret: bytes, token: str, *, sender:str, booking:str, purpose:str, digest_hex:str, generation:int) -> bool:
    if not isinstance(token,str): return False
    wanted=make_cvid(secret,sender=sender,booking=booking,purpose=purpose,digest_hex=digest_hex,generation=generation)
    return hmac.compare_digest(token,wanted)
