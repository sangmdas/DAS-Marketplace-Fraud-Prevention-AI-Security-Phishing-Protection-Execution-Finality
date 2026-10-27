import test from 'node:test';
import assert from 'node:assert/strict';
import {renderResult,validateResult,presentationGate,escapeHtml,DisclosureError} from './advertising.mjs';
const paid=()=>({listingId:'L1',paid:true,title:'Hotel',sponsor:'HotelCo',payer:'HotelCo',reason:'Paid placement',adLabel:'Advertisement',settingsUrl:'/ad-settings',policyVersion:5});
const clean=()=>({listingId:'L1',paid:false,title:'Unpaid listing'});
const matrix = [
 ['valid_organic',()=>assert.match(renderResult(clean()),/Unpaid listing/)],
 ['valid_paid',()=>assert.match(renderResult(paid()),/Advertisement/)],
 ['paid_without_label',()=>{let p=paid();delete p.adLabel;assert.throws(()=>renderResult(p),DisclosureError)}],
 ['paid_wrong_label',()=>{let p=paid();p.adLabel='Featured';assert.throws(()=>renderResult(p),DisclosureError)}],
 ['paid_without_payer',()=>{let p=paid();delete p.payer;assert.throws(()=>renderResult(p),DisclosureError)}],
 ['paid_without_sponsor',()=>{let p=paid();delete p.sponsor;assert.throws(()=>renderResult(p),DisclosureError)}],
 ['paid_without_reason',()=>{let p=paid();delete p.reason;assert.throws(()=>renderResult(p),DisclosureError)}],
 ['paid_without_controls',()=>{let p=paid();delete p.settingsUrl;assert.throws(()=>renderResult(p),DisclosureError)}],
 ['paid_controls_external_url',()=>{let p=paid();p.settingsUrl='https://external.test';assert.throws(()=>renderResult(p),DisclosureError)}],
 ['paid_without_policy_version',()=>{let p=paid();delete p.policyVersion;assert.throws(()=>renderResult(p),DisclosureError)}],
 ['missing_listing_id',()=>{let p=paid();delete p.listingId;assert.throws(()=>validateResult(p),DisclosureError)}],
 ['numeric_listing_id',()=>{let p=paid();p.listingId=123;assert.throws(()=>validateResult(p),DisclosureError)}],
 ['null_item',()=>assert.throws(()=>validateResult(null),DisclosureError)],
 ['string_item',()=>assert.throws(()=>validateResult('hotel'),DisclosureError)],
 ['organic_without_sponsor',()=>assert.equal(validateResult(clean()),true)],
 ['valid_render_gate',()=>{let p=paid();assert.equal(presentationGate(p,renderResult(p)).allowed,true)}],
 ['render_gate_dropped_label',()=>{let p=paid();assert.throws(()=>presentationGate(p,renderResult(p).replace('<strong role="note" class="ad-label">Advertisement</strong>','')),DisclosureError)}],
 ['render_gate_changed_payer',()=>{let p=paid();assert.throws(()=>presentationGate(p,renderResult(p).replace('Paid by: HotelCo','Paid by: Attacker')),DisclosureError)}],
 ['render_gate_changed_sponsor',()=>{let p=paid();assert.throws(()=>presentationGate(p,renderResult(p).replace('Sponsor: HotelCo','Sponsor: Attacker')),DisclosureError)}],
 ['render_gate_changed_reason',()=>{let p=paid();assert.throws(()=>presentationGate(p,renderResult(p).replace('Why shown: Paid placement','Why shown: Organic')),DisclosureError)}],
 ['render_gate_missing_controls',()=>{let p=paid();assert.throws(()=>presentationGate(p,renderResult(p).replace('Advertising controls','Other')),DisclosureError)}],
 ['html_title_escaped',()=>{let p=paid();p.title='<script>alert(1)</script>';let h=renderResult(p);assert.ok(!h.includes('<script>'));assert.ok(h.includes('&lt;script&gt;'))}],
 ['html_sponsor_escaped',()=>{let p=paid();p.sponsor='" onclick="evil';let h=renderResult(p);assert.ok(h.includes('&quot;'));assert.ok(!h.includes('Sponsor: " onclick'))}],
 ['html_reason_escaped',()=>{let p=paid();p.reason='<img src=x onerror=alert(1)>';let h=renderResult(p);assert.ok(!h.includes('<img'));assert.ok(h.includes('&lt;img'))}],
];
for (const [name,run] of matrix) test(name,run);
