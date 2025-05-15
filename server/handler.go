package server

import (
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"
)

// handles requests to update the server's configuration
func HandleConfigRequest(ts *TimecodeService) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Only POST method is allowed", http.StatusMethodNotAllowed)
			return
		}

		var newConfig ClientConfig
		decoder := json.NewDecoder(r.Body)
		if err := decoder.Decode(&newConfig); err != nil {
			http.Error(w, fmt.Sprintf("Failed to decode config: %v", err), http.StatusBadRequest)
			return
		}
		defer r.Body.Close()

		ts.UpdateConfig(newConfig)
		w.WriteHeader(http.StatusOK)
		fmt.Fprintln(w, "Configuration updated successfully")
	}
}

// Tracks client connections by IP
var clientTracker = &ClientTracker{
	clients: make(map[string]time.Time),
	timeout: 60 * time.Second, // consider disconnected after 60s
}

type ClientTracker struct {
	mu      sync.Mutex
	clients map[string]time.Time
	timeout time.Duration
}

func (ct *ClientTracker) Seen(ip string) (firstSeen bool) {
	ct.mu.Lock()
	defer ct.mu.Unlock()
	now := time.Now()
	_, exists := ct.clients[ip]
	ct.clients[ip] = now
	return !exists
}

func (ct *ClientTracker) CleanupAndGetDisconnected() []string {
	ct.mu.Lock()
	defer ct.mu.Unlock()
	now := time.Now()
	disconnected := []string{}
	for ip, lastSeen := range ct.clients {
		if now.Sub(lastSeen) > ct.timeout {
			disconnected = append(disconnected, ip)
			delete(ct.clients, ip)
		}
	}
	return disconnected
}

// Periodically check for disconnects
func StartDisconnectLogger() {
	go func() {
		for {
			time.Sleep(10 * time.Second)
			disconnected := clientTracker.CleanupAndGetDisconnected()
			for _, ip := range disconnected {
				fmt.Printf("[INFO] Client disconnected: %s\n", ip)
			}
		}
	}()
}

// wraps HandleConfigRequest to log client connections
func HandleConfigRequestWithLog(ts *TimecodeService, debug bool) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ip := r.RemoteAddr
		if debug {
			fmt.Printf("[DEBUG] /config endpoint hit from %s\n", ip)
		} else {
			if clientTracker.Seen(ip) {
				fmt.Printf("[INFO] Client connected: %s\n", ip)
			}
		}
		HandleConfigRequest(ts)(w, r)
	}
}

// handles requests for the current timecode
func HandleTimecodeRequest(ts *TimecodeService) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Only GET method is allowed", http.StatusMethodNotAllowed)
			return
		}
		timecode := ts.GetFormattedTimecode()
		w.Header().Set("Content-Type", "text/plain")
		fmt.Fprint(w, timecode)
	}
}

// wraps HandleTimecodeRequest to log client connections
func HandleTimecodeRequestWithLog(ts *TimecodeService, debug bool) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ip := r.RemoteAddr
		if debug {
			fmt.Printf("[DEBUG] /timecode endpoint hit from %s\n", ip)
		} else {
			if clientTracker.Seen(ip) {
				fmt.Printf("[INFO] Client connected: %s\n", ip)
			}
		}
		HandleTimecodeRequest(ts)(w, r)
	}
}
