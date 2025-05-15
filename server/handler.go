package server

import (
	"encoding/json"
	"fmt"
	"net/http"
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

// wraps HandleConfigRequest to log client connections
func HandleConfigRequestWithLog(ts *TimecodeService, debug bool) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if debug {
			fmt.Printf("[DEBUG] /config endpoint hit from %s\n", r.RemoteAddr)
		} else {
			fmt.Printf("[INFO] Client connected to /config from %s\n", r.RemoteAddr)
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
		if debug {
			fmt.Printf("[DEBUG] /timecode endpoint hit from %s\n", r.RemoteAddr)
		} else {
			fmt.Printf("[INFO] Client connected to /timecode from %s\n", r.RemoteAddr)
		}
		HandleTimecodeRequest(ts)(w, r)
	}
}
