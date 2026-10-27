"""Interactive local simulator API. NOT an internet-facing authorization service."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .core import Marketplace, Denied

app = FastAPI(title='DAS Marketplace Fraud Prevention - Research Demo', version='0.1.0')
store = Marketplace()

class Action(BaseModel):
    actor: str
    property: str
    kind: str
    body: dict

class Commit(BaseModel):
    grant: str
    sink: str
    actual_body: dict

@app.get('/healthz')
def health(): return {'status':'mock_only'}

@app.post('/v1/authorize')
def authorize(op: Action):
    try:
        return {'grant': store.authorize(op.actor,op.property,op.kind,op.body)}
    except Denied as exc:
        raise HTTPException(status_code=403, detail=str(exc))

@app.post('/v1/effect')
def effect(op: Commit):
    result=store.effect(op.grant,op.sink,op.actual_body)
    return result.__dict__

@app.get('/v1/audit')
def audit():
    return {'valid': store.audit_valid(), 'events':store.audit_count(), 'mock_effects':store.effect_count()}

@app.post('/demo/seed')
def seed():
    try:
        store.register('HOTEL-1',verified=True)
        store.property('PROP-1','HOTEL-1',verified=True,evidence='human-reviewed-fixture')
        store.booking('BOOK-1','PROP-1','GUEST-1','VERIFIED-MERCHANT',50000,'EUR','https://pay.example.test/booking')
    except Exception as exc:
        raise HTTPException(status_code=409,detail='demo already seeded') from exc
    return {'seeded':True,'note':'synthetic fixtures only'}
