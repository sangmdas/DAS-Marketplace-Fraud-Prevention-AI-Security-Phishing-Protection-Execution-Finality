import {renderResult,presentationGate} from './advertising.mjs';
const item={listingId:'PROP-1',paid:true,title:'Example hotel',sponsor:'Example Hotel',payer:'Example Hotel',reason:'paid placement',adLabel:'Advertisement',settingsUrl:'/ad-settings',policyVersion:2};
const rendered=renderResult(item);
console.log(presentationGate(item,rendered));
console.log(rendered);
