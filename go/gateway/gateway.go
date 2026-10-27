// Package gateway implements a non-production fast-path admission simulator.
// Identity, policy and beneficiary records are fixture inputs; the caller is
// assumed to be a trusted, authenticated orchestration component.
package gateway

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"
)

type Request struct {
	ID                    string `json:"id"`
	Kind                  string `json:"kind"`
	Actor                 string `json:"actor"`
	Property              string `json:"property"`
	Booking               string `json:"booking"`
	Recipient             string `json:"recipient"`
	AllowedRecipient      string `json:"allowed_recipient"`
	Merchant              string `json:"merchant"`
	AllowedMerchant       string `json:"allowed_merchant"`
	Amount                int64  `json:"amount"`
	AllowedAmount         int64  `json:"allowed_amount"`
	Currency              string `json:"currency"`
	AllowedCurrency       string `json:"allowed_currency"`
	VerifiedActor         bool   `json:"verified_actor"`
	VerifiedProperty      bool   `json:"verified_property"`
	HasDelegation         bool   `json:"has_delegation"`
	Risk                  int    `json:"risk"`
	Generation            uint64 `json:"generation"`
	CurrentGeneration     uint64 `json:"current_generation"`
	Advertised            bool   `json:"advertised"`
	Labelled              bool   `json:"labelled"`
	AuthorizedDestination bool   `json:"authorized_destination"`
	ExpiryUnix            int64  `json:"expiry_unix"`
}

type Decision struct {
	Allowed bool   `json:"allowed"`
	Reason  string `json:"reason"`
}

type Gate struct {
	mu    sync.Mutex
	seen  map[string]bool
	Clock func() time.Time
}

func NewGate() *Gate { return &Gate{seen: make(map[string]bool), Clock: time.Now} }

func (g *Gate) Admit(r Request) Decision {
	g.mu.Lock()
	defer g.mu.Unlock()
	deny := func(code string) Decision { return Decision{false, code} }
	if r.ID == "" || r.Actor == "" || r.Property == "" || r.Kind == "" {
		return deny("missing_operation_identity")
	}
	if g.seen[r.ID] {
		return deny("replayed_request")
	}
	if !r.VerifiedActor || !r.VerifiedProperty {
		return deny("identity_or_property_unverified")
	}
	if !r.HasDelegation {
		return deny("operation_outside_delegation")
	}
	if r.Risk >= 80 {
		return deny("high_risk")
	}
	if r.CurrentGeneration == 0 || r.Generation != r.CurrentGeneration {
		return deny("stale_generation")
	}
	if r.ExpiryUnix <= g.Clock().Unix() {
		return deny("expired")
	}
	switch r.Kind {
	case "publish":
		// A verified property is required for publication in the mock model.
	case "advertisement":
		if r.Advertised && !r.Labelled {
			return deny("advertisement_unlabelled")
		}
	case "message":
		if r.Booking == "" || r.Recipient == "" || r.Recipient != r.AllowedRecipient {
			return deny("message_booking_or_recipient_mismatch")
		}
		if !r.AuthorizedDestination {
			return deny("payment_link_not_authorized")
		}
	case "payment":
		if r.Booking == "" {
			return deny("missing_booking")
		}
		if r.Merchant != r.AllowedMerchant || r.Amount <= 0 || r.Amount != r.AllowedAmount || r.Currency != r.AllowedCurrency {
			return deny("payment_terms_mismatch")
		}
	case "export":
		if r.Booking == "" {
			return deny("missing_booking")
		}
	default:
		return deny("unknown_operation")
	}
	g.seen[r.ID] = true
	return Decision{true, "mock_admitted"}
}

func (g *Gate) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if r.Method == http.MethodGet && r.URL.Path == "/healthz" {
		json.NewEncoder(w).Encode(map[string]string{"status": "mock_only"})
		return
	}
	if r.Method != http.MethodPost || r.URL.Path != "/v1/admit" {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, 16384)
	defer r.Body.Close()
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	var in Request
	if err := decoder.Decode(&in); err != nil {
		http.Error(w, fmt.Sprintf("invalid JSON: %v", err), http.StatusBadRequest)
		return
	}
	var extra any
	if err := decoder.Decode(&extra); !errors.Is(err, io.EOF) {
		http.Error(w, "extra JSON content", http.StatusBadRequest)
		return
	}
	// Request may contain only one JSON object.
	d := g.Admit(in)
	if !d.Allowed {
		w.WriteHeader(http.StatusForbidden)
	}
	_ = json.NewEncoder(w).Encode(d)
}
