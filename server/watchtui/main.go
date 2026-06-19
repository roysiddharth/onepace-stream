package main

import (
	"fmt"
	"os"
	"os/exec"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/table"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

const remoteScript = `set -euo pipefail
SID=$(curl -s -o /dev/null -D - http://localhost:9091/transmission/rpc \
  | awk -F': ' '/^X-Transmission-Session-Id:/{print $2}' | tr -d '\r')
curl -s -H "X-Transmission-Session-Id: $SID" \
  -d '{"method":"torrent-get","arguments":{"fields":["name","percentDone","eta","rateDownload","rateUpload","status","peersConnected"]}}' \
  http://localhost:9091/transmission/rpc \
| jq -r '
  def human_rate:
    if . == 0 then "-"
    elif . < 1024 then "\(.)B/s"
    elif . < 1048576 then "\(. / 1024 | floor)KB/s"
    else "\(. / 1048576 * 10 | floor / 10)MB/s"
    end;
  def status_name:
    if . == 0 then "Stopped"
    elif . == 1 then "QueueCheck"
    elif . == 2 then "Checking"
    elif . == 3 then "QueueDL"
    elif . == 4 then "Downloading"
    elif . == 5 then "QueueSeed"
    elif . == 6 then "Seeding"
    else "Unknown"
    end;
  (.arguments.torrents[] | [
      (.name | if length > 40 then .[0:37] + "..." else . end),
      ((.percentDone * 100 | floor | tostring) + "%"),
      (.status | status_name),
      (.rateDownload | human_rate),
      (.rateUpload | human_rate),
      (if .eta < 0 then "-" else (.eta | tostring) + "s" end),
      (.peersConnected | tostring)
  ])
  | @tsv
'
`

// Lower = higher in the table. Active transfers float to the top.
var statusRank = map[string]int{
	"Downloading": 0,
	"QueueDL":     1,
	"Checking":    2,
	"QueueCheck":  3,
	"Seeding":     4,
	"QueueSeed":   5,
	"Stopped":     6,
}

var statusColor = map[string]lipgloss.Color{
	"Downloading": lipgloss.Color("10"),
	"Seeding":     lipgloss.Color("12"),
	"Stopped":     lipgloss.Color("8"),
	"QueueDL":     lipgloss.Color("11"),
	"QueueSeed":   lipgloss.Color("11"),
	"Checking":    lipgloss.Color("14"),
	"QueueCheck":  lipgloss.Color("14"),
}

type rowsMsg []table.Row
type errMsg error

type model struct {
	table    table.Model
	interval time.Duration
	updated  time.Time
	err      error
}

func fetchRowsCmd() tea.Msg {
	server := os.Getenv("ONEPACE_SERVER")
	if server == "" {
		server = "server-node-0"
	}
	cmd := exec.Command("ssh", server, "bash", "-s")
	cmd.Stdin = strings.NewReader(remoteScript)
	out, err := cmd.Output()
	if err != nil {
		return errMsg(err)
	}
	rows := make([]table.Row, 0)
	for _, line := range strings.Split(strings.TrimRight(string(out), "\n"), "\n") {
		if line == "" {
			continue
		}
		fields := strings.Split(line, "\t")
		if len(fields) != 7 {
			continue
		}
		rows = append(rows, table.Row(fields))
	}
	sort.SliceStable(rows, func(i, j int) bool {
		ri, ok := statusRank[rows[i][2]]
		if !ok {
			ri = 99
		}
		rj, ok := statusRank[rows[j][2]]
		if !ok {
			rj = 99
		}
		return ri < rj
	})
	return rowsMsg(rows)
}

func tick(interval time.Duration) tea.Cmd {
	return tea.Tick(interval, func(time.Time) tea.Msg { return fetchRowsCmd() })
}

func newModel(interval time.Duration) model {
	columns := []table.Column{
		{Title: "NAME", Width: 40},
		{Title: "DONE%", Width: 6},
		{Title: "STATUS", Width: 11},
		{Title: "DOWN", Width: 9},
		{Title: "UP", Width: 9},
		{Title: "ETA", Width: 7},
		{Title: "PEERS", Width: 5},
	}
	t := table.New(table.WithColumns(columns), table.WithFocused(true))
	t.SetStyles(table.DefaultStyles())
	return model{table: t, interval: interval}
}

func (m model) Init() tea.Cmd {
	return tea.Batch(fetchRowsCmd, tick(m.interval))
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.String() == "q" || msg.String() == "ctrl+c" {
			return m, tea.Quit
		}
		var cmd tea.Cmd
		m.table, cmd = m.table.Update(msg)
		return m, cmd
	case rowsMsg:
		m.table.SetRows(coloredRows([]table.Row(msg)))
		m.updated = time.Now()
		m.err = nil
		return m, tick(m.interval)
	case errMsg:
		m.err = msg
		return m, tick(m.interval)
	}
	return m, nil
}

func coloredRows(rows []table.Row) []table.Row {
	for i, r := range rows {
		if color, ok := statusColor[r[2]]; ok {
			style := lipgloss.NewStyle().Foreground(color)
			r2 := append(table.Row{}, r...)
			r2[2] = style.Render(r[2])
			rows[i] = r2
		}
	}
	return rows
}

func (m model) View() string {
	var b strings.Builder
	b.WriteString(m.table.View())
	b.WriteString("\n")
	if m.err != nil {
		b.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("9")).Render("error: "+m.err.Error()) + "\n")
	}
	if !m.updated.IsZero() {
		b.WriteString(fmt.Sprintf("updated: %s  (q to quit)\n", m.updated.Format("15:04:05")))
	}
	return b.String()
}

func main() {
	interval := 8 * time.Second
	if len(os.Args) > 1 {
		if secs, err := strconv.Atoi(os.Args[1]); err == nil {
			interval = time.Duration(secs) * time.Second
		}
	}
	p := tea.NewProgram(newModel(interval))
	if _, err := p.Run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
