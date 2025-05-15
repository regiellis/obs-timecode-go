package server

// ClientConfig represents the configuration sent by the Lua client
type ClientConfig struct {
	SourceName string `json:"source_name"` // For server logging/awareness, not directly used for timegen
	TimeMode   string `json:"time_mode"`   // "24 Hour", "12 Hour", "12 Hour + AM/PM"
	ShowFrame  bool   `json:"show_frame"`
	ShowDate   bool   `json:"show_date"`
	ShowUTC    bool   `json:"show_utc"`
	PreText    string `json:"pre_text"`
	PostText   string `json:"post_text"`
	FPS        int    `json:"fps"` // Frames per second for frame counting
}
