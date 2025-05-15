package server

import (
	"fmt"
	"sync"
	"time"
)

type TimeProvider func() time.Time

type TimecodeService struct {
	mu                sync.Mutex
	config            ClientConfig
	lastSecond        int
	currentFrame      int
	lastNanosecondDiv int64 // Used for more precise frame reset with monotonic time
	timeProvider      TimeProvider
}

func NewTimecodeService(defaultFPS int) *TimecodeService {
	return &TimecodeService{
		config: ClientConfig{
			TimeMode:  "24 Hour",
			ShowFrame: false,
			ShowDate:  false,
			ShowUTC:   false,
			FPS:       defaultFPS,
		},
		lastSecond:   -1,
		currentFrame: 0,
		timeProvider: time.Now,
	}
}

func (ts *TimecodeService) SetTimeProvider(tp TimeProvider) {
	ts.mu.Lock()
	defer ts.mu.Unlock()
	ts.timeProvider = tp
}

func (ts *TimecodeService) UpdateConfig(newConfig ClientConfig) {
	ts.mu.Lock()
	defer ts.mu.Unlock()
	if newConfig.FPS <= 0 {
		newConfig.FPS = 30 // Fallback FPS
	}
	ts.config = newConfig
	ts.lastSecond = -1
	ts.currentFrame = 0
	ts.lastNanosecondDiv = -1

	fmt.Printf("Server config updated: %+v\n", ts.config)
}

func (ts *TimecodeService) GetFormattedTimecode() string {
	ts.mu.Lock()
	defer ts.mu.Unlock()

	now := ts.timeProvider()
	if ts.config.ShowUTC {
		now = now.UTC()
	}

	// --- Monotonic, elapsed-time-based frame calculation ---
	var frameStr string
	if ts.config.ShowFrame {
		fps := ts.config.FPS
		if fps <= 0 {
			fps = 30
		}
		nanosPerFrame := int64(1e9 / fps)
		// Use the start of the current second as a reference
		startOfSecond := now.Truncate(time.Second)
		elapsedNanos := now.Sub(startOfSecond).Nanoseconds()
		frameVal := int(elapsedNanos/nanosPerFrame) % fps
		frameStr = fmt.Sprintf(":%02d", frameVal)
	}

	// Determine base time format defaults to 24-hour format
	var timeFormat string
	switch ts.config.TimeMode {
	case "12 Hour", "12 Hour + AM/PM":
		timeFormat = "03:04:05"
	default:
		timeFormat = "15:04:05"
	}

	// Prepend date if requested
	dateStr := ""
	if ts.config.ShowDate {
		dateStr = now.Format("2006-01-02 ")
	}

	timeStr := now.Format(timeFormat)

	// Append AM/PM if requested
	ampmStr := ""
	if ts.config.TimeMode == "12 Hour + AM/PM" {
		ampmStr = " " + now.Format("PM")
	}

	return fmt.Sprintf("%s%s%s%s%s%s", ts.config.PreText, dateStr, timeStr, frameStr, ampmStr, ts.config.PostText)
}
