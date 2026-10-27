/** Non-production advertising-presentation contract. Real browsers need DOM, a11y, and visual tests. */
export class DisclosureError extends Error {}
export function validateResult(item) {
  if (!item || typeof item !== 'object' || !item.listingId || typeof item.listingId !== 'string') throw new DisclosureError('invalid_listing');
  if (item.paid === true) {
    if (!item.sponsor || !item.payer || !item.reason || !item.adLabel || item.adLabel.toLowerCase() !== 'advertisement') {
      throw new DisclosureError('missing_paid_disclosure');
    }
    if (!item.settingsUrl || !item.settingsUrl.startsWith('/')) throw new DisclosureError('missing_ad_controls');
    if (item.policyVersion === undefined || item.policyVersion === null) throw new DisclosureError('missing_policy_version');
  }
  return true;
}
export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
}
export function renderResult(item) {
  validateResult(item);
  const label = item.paid ? `<strong role="note" class="ad-label">${escapeHtml(item.adLabel)}</strong>` : '';
  const disclosure = item.paid ? `<p class="ad-info">Sponsor: ${escapeHtml(item.sponsor)}; Paid by: ${escapeHtml(item.payer)}; Why shown: ${escapeHtml(item.reason)}</p><a href="${escapeHtml(item.settingsUrl)}">Advertising controls</a>` : '';
  return `<article data-listing="${escapeHtml(item.listingId)}" data-policy="${escapeHtml(item.policyVersion??'none')}">${label}<h2>${escapeHtml(item.title||'Accommodation')}</h2>${disclosure}</article>`;
}
export function presentationGate(item, claimedHtml) {
  const expected=renderResult(item);
  if (expected !== claimedHtml) throw new DisclosureError('final_presentation_mismatch');
  return {allowed:true, reason:'presentation_contract_matches'};
}
