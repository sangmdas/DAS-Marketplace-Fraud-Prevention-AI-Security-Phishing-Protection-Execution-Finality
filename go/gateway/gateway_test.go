package gateway

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"
)

func fixture() Request {
	return Request{ID: "case-1", Kind: "message", Actor: "hotel", Property: "P1", Booking: "B1", Recipient: "guest", AllowedRecipient: "guest", Merchant: "hotel-merchant", AllowedMerchant: "hotel-merchant", Amount: 500, AllowedAmount: 500, Currency: "EUR", AllowedCurrency: "EUR", VerifiedActor: true, VerifiedProperty: true, HasDelegation: true, Risk: 0, Generation: 8, CurrentGeneration: 8, AuthorizedDestination: true, ExpiryUnix: time.Now().Add(time.Minute).Unix()}
}

func TestAdmissionMatrix(t *testing.T) {
	cases := []struct {
		name    string
		modify  func(*Request)
		allowed bool
		reason  string
	}{
		{"valid_message", func(r *Request) {}, true, "mock_admitted"},
		{"wrong_recipient", func(r *Request) { r.Recipient = "other" }, false, "message_booking_or_recipient_mismatch"},
		{"missing_booking", func(r *Request) { r.Booking = "" }, false, "message_booking_or_recipient_mismatch"},
		{"payment_link_out_of_scope", func(r *Request) { r.AuthorizedDestination = false }, false, "payment_link_not_authorized"},
		{"unverified_actor", func(r *Request) { r.VerifiedActor = false }, false, "identity_or_property_unverified"},
		{"unverified_property", func(r *Request) { r.VerifiedProperty = false }, false, "identity_or_property_unverified"},
		{"missing_delegation", func(r *Request) { r.HasDelegation = false }, false, "operation_outside_delegation"},
		{"high_risk_threshold", func(r *Request) { r.Risk = 80 }, false, "high_risk"},
		{"very_high_risk", func(r *Request) { r.Risk = 99 }, false, "high_risk"},
		{"stale_generation", func(r *Request) { r.Generation = 7 }, false, "stale_generation"},
		{"unknown_current_generation", func(r *Request) { r.CurrentGeneration = 0 }, false, "stale_generation"},
		{"expired", func(r *Request) { r.ExpiryUnix = time.Now().Add(-time.Minute).Unix() }, false, "expired"},
		{"missing_actor", func(r *Request) { r.Actor = "" }, false, "missing_operation_identity"},
		{"missing_property", func(r *Request) { r.Property = "" }, false, "missing_operation_identity"},
		{"invalid_kind", func(r *Request) { r.Kind = "refund_to_anyone" }, false, "unknown_operation"},
		{"valid_payment", func(r *Request) { r.Kind = "payment" }, true, "mock_admitted"},
		{"payment_merchant_substitution", func(r *Request) { r.Kind = "payment"; r.Merchant = "attacker" }, false, "payment_terms_mismatch"},
		{"payment_amount_substitution", func(r *Request) { r.Kind = "payment"; r.Amount = 600 }, false, "payment_terms_mismatch"},
		{"payment_currency_substitution", func(r *Request) { r.Kind = "payment"; r.Currency = "USD" }, false, "payment_terms_mismatch"},
		{"unlabelled_boosted_ad", func(r *Request) { r.Kind = "advertisement"; r.Advertised = true; r.Labelled = false }, false, "advertisement_unlabelled"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			g := NewGate()
			r := fixture()
			tc.modify(&r)
			d := g.Admit(r)
			if d.Allowed != tc.allowed || d.Reason != tc.reason {
				t.Fatalf("%+v expected allow %v reason %s", d, tc.allowed, tc.reason)
			}
		})
	}
}

func TestReplayAndValidAd(t *testing.T) {
	g := NewGate()
	r := fixture()
	r.Kind = "advertisement"
	r.Advertised = true
	r.Labelled = true
	if !g.Admit(r).Allowed {
		t.Fatal("valid attributed placement rejected")
	}
	if g.Admit(r).Reason != "replayed_request" {
		t.Fatal("replay accepted")
	}
}
func TestConcurrentSingleUse(t *testing.T) {
	g := NewGate()
	r := fixture()
	var wg sync.WaitGroup
	var mu sync.Mutex
	allowed := 0
	for i := 0; i < 32; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if g.Admit(r).Allowed {
				mu.Lock()
				allowed++
				mu.Unlock()
			}
		}()
	}
	wg.Wait()
	if allowed != 1 {
		t.Fatalf("got %d admissions", allowed)
	}
}
func TestHTTPWellFormedAndMalformed(t *testing.T) {
	g := NewGate()
	payload, _ := json.Marshal(fixture())
	rr := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/v1/admit", bytes.NewReader(payload))
	g.ServeHTTP(rr, req)
	if rr.Code != 200 {
		t.Fatalf("expected 200, got %d", rr.Code)
	}
	bad := httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodPost, "/v1/admit", bytes.NewBufferString(`{"nonsense":true}`))
	g.ServeHTTP(bad, req)
	if bad.Code != 400 {
		t.Fatalf("malformed object returned %d", bad.Code)
	}
}
func TestHTTPMethodAndBodyRestrictions(t *testing.T) {
	g := NewGate()
	health := httptest.NewRecorder()
	g.ServeHTTP(health, httptest.NewRequest(http.MethodGet, "/healthz", nil))
	if health.Code != 200 {
		t.Fatal("health failed")
	}
	wrong := httptest.NewRecorder()
	g.ServeHTTP(wrong, httptest.NewRequest(http.MethodPut, "/v1/admit", nil))
	if wrong.Code != 404 {
		t.Fatal("method accepted")
	}
	huge := httptest.NewRecorder()
	g.ServeHTTP(huge, httptest.NewRequest(http.MethodPost, "/v1/admit", bytes.NewBuffer(bytes.Repeat([]byte{'x'}, 20000))))
	if huge.Code != 400 {
		t.Fatalf("oversize status %d", huge.Code)
	}
}
