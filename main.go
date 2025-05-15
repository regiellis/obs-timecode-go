package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/beevik/ntp"
	"github.com/regiellis/obs-timecode-go/server"

	"github.com/charmbracelet/lipgloss"
	"github.com/spf13/cobra"
)

var (
	port        int
	defaultFps  int
	timeService *server.TimecodeService
	ntpServer   string
	debug       bool // Add debug flag
)

// NTP sync interval in seconds
type ntpTimeProvider struct {
	server   string
	lastSync time.Time
	offset   time.Duration
}

func newNtpTimeProvider(server string) *ntpTimeProvider {
	return &ntpTimeProvider{server: server}
}

func (n *ntpTimeProvider) Now() time.Time {
	if n.offset == 0 || time.Since(n.lastSync) > 10*time.Minute {
		offset, err := getNtpOffset(n.server)
		if err == nil {
			n.offset = offset
			n.lastSync = time.Now()
		} else {
			log.Printf("[WARN] NTP sync failed: %v, using system time", err)
		}
	}
	return time.Now().Add(n.offset)
}

func getNtpOffset(server string) (time.Duration, error) {
	resp, err := ntp.Query(server)
	if err != nil {
		return 0, err
	}
	return resp.ClockOffset, nil
}

func TimeCodeServer(cmd *cobra.Command, args []string) {
	// Style for server startup message
	var style = lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#FAFAFA")).
		Background(lipgloss.Color("#7D56F4")).
		PaddingLeft(1).
		PaddingRight(1)

	fmt.Println(style.Render(fmt.Sprintf("OBS Timecode Server starting on :%d", port)))
	fmt.Println(lipgloss.NewStyle().Italic(true).Render(fmt.Sprintf("Default FPS set to: %d. Lua client can override via /config endpoint.", defaultFps)))
	if debug {
		fmt.Println(lipgloss.NewStyle().Foreground(lipgloss.Color("#FFD700")).Render("[DEBUG] Verbose output enabled."))
	}

	timeProvider := newNtpTimeProvider(ntpServer)
	timeService.SetTimeProvider(func() time.Time { return timeProvider.Now() })

	http.HandleFunc("/timecode", server.HandleTimecodeRequestWithLog(timeService, debug))
	http.HandleFunc("/config", server.HandleConfigRequestWithLog(timeService, debug))

	log.Printf("Listening on port %d...\n", port)
	if err := http.ListenAndServe(fmt.Sprintf(":%d", port), nil); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

var rootCmd = &cobra.Command{
	Use:   "obs-timecodeserver",
	Short: "A precise timecode server for OBS",
	PersistentPreRun: func(cmd *cobra.Command, args []string) {
		// Initialize TimecodeService with default FPS
		// This FPS can be overridden by the Lua client via /config
		timeService = server.NewTimecodeService(defaultFps)
	},
	Run: func(cmd *cobra.Command, args []string) {
		TimeCodeServer(cmd, args)
	},
}

func init() {
	rootCmd.PersistentFlags().IntVarP(&port, "port", "p", 8080, "Port to run the server on")
	rootCmd.PersistentFlags().IntVarP(&defaultFps, "fps", "f", 30, "Default frames per second for timecode")
	rootCmd.PersistentFlags().StringVar(&ntpServer, "ntp", "pool.ntp.org", "NTP server for time synchronization")
	rootCmd.PersistentFlags().BoolVar(&debug, "debug", false, "Enable debug output")
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
