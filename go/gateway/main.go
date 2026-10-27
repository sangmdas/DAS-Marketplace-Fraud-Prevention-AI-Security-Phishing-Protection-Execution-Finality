//go:build ignore

package main

// Run `go run main.go` from the go/gateway folder.
import (
	"example.org/das-marketplace-gateway"
	"fmt"
	"net/http"
)

func main() {
	fmt.Println("MOCK local gateway at 127.0.0.1:8099")
	panic(http.ListenAndServe("127.0.0.1:8099", gateway.NewGate()))
}
