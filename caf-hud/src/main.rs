use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyEventKind},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    backend::CrosstermBackend,
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Wrap},
    Frame, Terminal,
};
use std::{
    fs,
    io,
    path::{Path, PathBuf},
    time::{Duration, Instant},
};

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
enum HudMode {
    Idle,
    Active,
}

#[derive(Debug, Clone, Default)]
struct LeadStatus {
    role: String,
    status: String, // running | done | failed | aborted | pending
}

#[derive(Debug, Clone, Default)]
struct WorkingMemoryEntry {
    lead: String,
    summary: String,
    why: String,
    ts: String,
}

#[derive(Debug, Clone, Default)]
struct PendingQuestion {
    id: String,
    lead: String,
    question: String,
    critical: bool,
}

#[derive(Debug, Clone, Default)]
struct JobInfo {
    orch_id: String,
    task_line: String,
    criteria: Vec<(bool, String)>,
    verdict: String,
    lead_statuses: Vec<LeadStatus>,
    working_memory: Vec<WorkingMemoryEntry>,
    pending_questions: Vec<PendingQuestion>,
}

#[derive(Debug, Clone, Default)]
struct IdleSummary {
    last_orch_id: String,
    task_line: String,
    criteria: Vec<(bool, String)>,
    verdict: String,
    hook_count: usize,
    agent_count: usize,
    skill_count: usize,
}

struct App {
    mode: HudMode,
    // Active mode
    active_job: Option<JobInfo>,
    // Job history tabs (newest first, index 0 = active/newest)
    job_tabs: Vec<String>, // orch_ids
    selected_tab: usize,
    tab_list_state: ListState,
    // Idle mode
    idle_summary: IdleSummary,
    // Polling
    last_poll: Instant,
    poll_interval: Duration,
    should_quit: bool,
}

impl App {
    fn new() -> Self {
        let mut s = Self {
            mode: HudMode::Idle,
            active_job: None,
            job_tabs: Vec::new(),
            selected_tab: 0,
            tab_list_state: ListState::default(),
            idle_summary: IdleSummary::default(),
            last_poll: Instant::now(),
            poll_interval: Duration::from_secs(1),
            should_quit: false,
        };
        s.tab_list_state.select(Some(0));
        s
    }

    fn poll(&mut self) {
        if self.last_poll.elapsed() < self.poll_interval {
            return;
        }
        self.last_poll = Instant::now();

        let orch_base = Path::new("/tmp/caf_orch");
        let job_dirs = find_orch_dirs(orch_base);

        if job_dirs.is_empty() {
            self.mode = HudMode::Idle;
            self.active_job = None;
            self.job_tabs.clear();
            self.load_idle_summary();
        } else {
            self.mode = HudMode::Active;
            // Build tab list (newest first)
            self.job_tabs = job_dirs.iter().map(|p| {
                p.file_name().unwrap_or_default().to_string_lossy().to_string()
            }).collect();

            if self.selected_tab >= self.job_tabs.len() {
                self.selected_tab = 0;
            }

            // Load the selected job
            if let Some(orch_id) = self.job_tabs.get(self.selected_tab) {
                let job_path = orch_base.join(orch_id);
                self.active_job = Some(load_job_info(&job_path, orch_id));
            }
        }
    }

    fn load_idle_summary(&mut self) {
        // Try to find last completed job from ~/.claude/data/orch_results/
        let results_dir = dirs_home().join(".claude").join("data").join("orch_results");
        if results_dir.exists() {
            if let Ok(mut entries) = fs::read_dir(&results_dir) {
                let mut dirs: Vec<PathBuf> = Vec::new();
                while let Some(Ok(e)) = entries.next() {
                    if e.path().is_dir() {
                        dirs.push(e.path());
                    }
                }
                dirs.sort_by(|a, b| {
                    let mt_a = a.metadata().and_then(|m| m.modified()).ok();
                    let mt_b = b.metadata().and_then(|m| m.modified()).ok();
                    mt_b.cmp(&mt_a)
                });
                if let Some(last_dir) = dirs.first() {
                    let orch_id = last_dir
                        .file_name()
                        .unwrap_or_default()
                        .to_string_lossy()
                        .to_string();
                    self.idle_summary.last_orch_id = orch_id;
                    // Try to read acceptance_criteria.md from results dir
                    let ac_path = last_dir.join("acceptance_criteria.md");
                    let (task, criteria) = parse_acceptance_criteria(&ac_path);
                    self.idle_summary.task_line = task;
                    self.idle_summary.criteria = criteria;
                    // Try evaluation_report.md
                    let er_path = last_dir.join("evaluation_report.md");
                    self.idle_summary.verdict = parse_verdict(&er_path);
                }
            }
        }

        // System status from CLAUDE.md
        // Structure lines look like: "global-hooks/        45 hooks across 16 events (...)"
        // The number always appears after the "/" — split there and extract.
        let claude_md = caf_dir().join("CLAUDE.md");
        if let Ok(text) = fs::read_to_string(&claude_md) {
            for line in text.lines() {
                let after_slash = line.find('/').map(|i| line[i + 1..].trim());
                if line.contains("hooks across") {
                    if let Some(n) = after_slash.and_then(extract_leading_number) {
                        self.idle_summary.hook_count = n;
                    }
                } else if line.contains(" agents") && line.starts_with("global-agents") {
                    if let Some(n) = after_slash.and_then(extract_leading_number) {
                        self.idle_summary.agent_count = n;
                    }
                } else if line.contains(" skills") && line.starts_with("global-skills") {
                    if let Some(n) = after_slash.and_then(extract_leading_number) {
                        self.idle_summary.skill_count = n;
                    }
                }
            }
        }
    }

    fn next_tab(&mut self) {
        if self.job_tabs.is_empty() {
            return;
        }
        self.selected_tab = (self.selected_tab + 1) % self.job_tabs.len();
        self.tab_list_state.select(Some(self.selected_tab));
    }

    fn prev_tab(&mut self) {
        if self.job_tabs.is_empty() {
            return;
        }
        if self.selected_tab == 0 {
            self.selected_tab = self.job_tabs.len() - 1;
        } else {
            self.selected_tab -= 1;
        }
        self.tab_list_state.select(Some(self.selected_tab));
    }

    fn select_tab_by_number(&mut self, n: usize) {
        let idx = n.saturating_sub(1);
        if idx < self.job_tabs.len() {
            self.selected_tab = idx;
            self.tab_list_state.select(Some(self.selected_tab));
        }
    }
}

// ---------------------------------------------------------------------------
// File parsing helpers
// ---------------------------------------------------------------------------

fn dirs_home() -> PathBuf {
    std::env::var("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/tmp"))
}

fn caf_dir() -> PathBuf {
    // Resolve from binary location: target/release/caf-hud → repo root
    std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().and_then(|p| p.parent()).and_then(|p| p.parent()).map(|p| p.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("/tmp"))
}

fn find_orch_dirs(base: &Path) -> Vec<PathBuf> {
    if !base.exists() {
        return Vec::new();
    }
    let mut dirs: Vec<PathBuf> = Vec::new();
    if let Ok(entries) = fs::read_dir(base) {
        for entry in entries.flatten() {
            let p = entry.path();
            if p.is_dir() && p.join("acceptance_criteria.md").exists() {
                dirs.push(p);
            }
        }
    }
    // Sort newest first by mtime
    dirs.sort_by(|a, b| {
        let mt_a = a.metadata().and_then(|m| m.modified()).ok();
        let mt_b = b.metadata().and_then(|m| m.modified()).ok();
        mt_b.cmp(&mt_a)
    });
    dirs
}

fn parse_acceptance_criteria(path: &Path) -> (String, Vec<(bool, String)>) {
    let text = match fs::read_to_string(path) {
        Ok(t) => t,
        Err(_) => return (String::new(), Vec::new()),
    };
    let mut task_line = String::new();
    let mut criteria = Vec::new();
    for line in text.lines() {
        if line.contains("**Task**:") {
            task_line = line
                .split("**Task**:")
                .nth(1)
                .unwrap_or("")
                .trim()
                .to_string();
        } else if line.starts_with("- [x]") || line.starts_with("- [X]") {
            let text = line[5..].trim().to_string();
            criteria.push((true, text));
        } else if line.starts_with("- [ ]") {
            let text = line[5..].trim().to_string();
            criteria.push((false, text));
        }
    }
    (task_line, criteria)
}

fn parse_verdict(path: &Path) -> String {
    let text = match fs::read_to_string(path) {
        Ok(t) => t,
        Err(_) => return String::new(),
    };
    let mut in_verdict = false;
    for line in text.lines() {
        if line.starts_with("## Overall Verdict") {
            in_verdict = true;
            continue;
        }
        if in_verdict {
            let trimmed = line.trim();
            if !trimmed.is_empty() {
                return trimmed.chars().take(80).collect();
            }
        }
    }
    String::new()
}

fn parse_lead_statuses(base: &Path) -> Vec<LeadStatus> {
    // Dynamic: scan for any *.status file so custom lead names (api-lead,
    // backend-lead, design-lead, etc.) show up alongside standard ones.
    let mut statuses = Vec::new();
    if let Ok(entries) = fs::read_dir(base) {
        let mut pairs: Vec<(String, String)> = Vec::new();
        for entry in entries.flatten() {
            let p = entry.path();
            if p.extension().and_then(|e| e.to_str()) == Some("status") {
                let role = p
                    .file_stem()
                    .and_then(|s| s.to_str())
                    .unwrap_or("unknown")
                    .to_string();
                if let Ok(text) = fs::read_to_string(&p) {
                    if let Ok(v) = serde_json::from_str::<serde_json::Value>(&text) {
                        let status = v["status"].as_str().unwrap_or("unknown").to_string();
                        pairs.push((role, status));
                    }
                }
            }
        }
        // Sort alphabetically for stable display order
        pairs.sort_by(|a, b| a.0.cmp(&b.0));
        for (role, status) in pairs {
            statuses.push(LeadStatus { role, status });
        }
    }
    statuses
}

fn parse_working_memory(path: &Path) -> Vec<WorkingMemoryEntry> {
    let text = match fs::read_to_string(path) {
        Ok(t) => t,
        Err(_) => return Vec::new(),
    };
    let mut entries = Vec::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        if let Ok(v) = serde_json::from_str::<serde_json::Value>(line) {
            let lead = v["lead"]
                .as_str()
                .or_else(|| v["role"].as_str())
                .or_else(|| v["agent"].as_str())
                .unwrap_or("?")
                .to_string();
            let summary = v["summary"]
                .as_str()
                .or_else(|| v["content"].as_str())
                .or_else(|| v["text"].as_str())
                .unwrap_or("")
                .to_string();
            let why = v["why"]
                .as_str()
                .or_else(|| v["reason"].as_str())
                .unwrap_or("")
                .to_string();
            let ts = v["ts"]
                .as_str()
                .or_else(|| v["timestamp"].as_str())
                .unwrap_or("")
                .to_string();
            entries.push(WorkingMemoryEntry { lead, summary, why, ts });
        }
    }
    // Return last 5
    let len = entries.len();
    if len > 5 {
        entries[len - 5..].to_vec()
    } else {
        entries
    }
}

fn parse_pending_questions(path: &Path) -> Vec<PendingQuestion> {
    let text = match fs::read_to_string(path) {
        Ok(t) => t,
        Err(_) => return Vec::new(),
    };
    let mut questions = Vec::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        if let Ok(v) = serde_json::from_str::<serde_json::Value>(line) {
            if v["status"].as_str() != Some("pending") {
                continue;
            }
            let id = match &v["id"] {
                serde_json::Value::String(s) => s.clone(),
                serde_json::Value::Number(n) => n.to_string(),
                _ => "?".to_string(),
            };
            let lead = v["lead"]
                .as_str()
                .or_else(|| v["from"].as_str())
                .unwrap_or("?")
                .to_string();
            let question = v["question"]
                .as_str()
                .or_else(|| v["text"].as_str())
                .unwrap_or("")
                .chars()
                .take(60)
                .collect();
            let critical = v["critical"].as_bool().unwrap_or(false);
            questions.push(PendingQuestion { id, lead, question, critical });
        }
    }
    questions
}

fn load_job_info(base: &Path, orch_id: &str) -> JobInfo {
    let (task_line, criteria) = parse_acceptance_criteria(&base.join("acceptance_criteria.md"));
    let verdict = parse_verdict(&base.join("evaluation_report.md"));
    let lead_statuses = parse_lead_statuses(base);
    let working_memory = parse_working_memory(&base.join("shared").join("working_memory.jsonl"));
    let pending_questions = parse_pending_questions(&base.join("shared").join("questions.jsonl"));

    JobInfo {
        orch_id: orch_id.to_string(),
        task_line,
        criteria,
        verdict,
        lead_statuses,
        working_memory,
        pending_questions,
    }
}

fn extract_leading_number(s: &str) -> Option<usize> {
    let num_str: String = s.chars().take_while(|c| c.is_ascii_digit()).collect();
    if num_str.is_empty() { None } else { num_str.parse().ok() }
}

// ---------------------------------------------------------------------------
// UI rendering
// ---------------------------------------------------------------------------

fn render(f: &mut Frame, app: &App) {
    match app.mode {
        HudMode::Idle => render_idle(f, app),
        HudMode::Active => render_active(f, app),
    }
}

fn render_idle(f: &mut Frame, app: &App) {
    let area = f.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(0),
            Constraint::Length(3),
        ])
        .split(area);

    // Header
    let header = Paragraph::new(Line::from(vec![
        Span::styled(" caf-hud ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
        Span::styled("| idle — no active job", Style::default().fg(Color::DarkGray)),
    ]))
    .block(Block::default().borders(Borders::ALL));
    f.render_widget(header, chunks[0]);

    // Content area
    let content_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(60), Constraint::Percentage(40)])
        .split(chunks[1]);

    // Last job summary
    let idle = &app.idle_summary;
    let mut lines = vec![];

    if idle.last_orch_id.is_empty() {
        lines.push(Line::from(Span::styled(
            "No previous jobs found.",
            Style::default().fg(Color::DarkGray),
        )));
    } else {
        lines.push(Line::from(vec![
            Span::styled("Last job: ", Style::default().fg(Color::Yellow)),
            Span::raw(idle.last_orch_id.clone()),
        ]));
        if !idle.task_line.is_empty() {
            lines.push(Line::from(vec![
                Span::styled("Task: ", Style::default().fg(Color::Cyan)),
                Span::raw(idle.task_line.clone()),
            ]));
        }
        lines.push(Line::from(""));
        lines.push(Line::from(Span::styled(
            "Acceptance criteria:",
            Style::default().add_modifier(Modifier::BOLD),
        )));
        for (done, text) in &idle.criteria {
            let (mark, color) = if *done {
                ("[x]", Color::Green)
            } else {
                ("[ ]", Color::DarkGray)
            };
            lines.push(Line::from(vec![
                Span::styled(format!("  {} ", mark), Style::default().fg(color)),
                Span::raw(text.clone()),
            ]));
        }
        if !idle.verdict.is_empty() {
            lines.push(Line::from(""));
            lines.push(Line::from(vec![
                Span::styled("Verdict: ", Style::default().fg(Color::Magenta)),
                Span::raw(idle.verdict.clone()),
            ]));
        }
    }

    let last_job = Paragraph::new(lines)
        .block(
            Block::default()
                .title(" Last Completed Job ")
                .borders(Borders::ALL),
        )
        .wrap(Wrap { trim: true });
    f.render_widget(last_job, content_chunks[0]);

    // System status
    let sys_lines = vec![
        Line::from(vec![
            Span::styled("Hooks:  ", Style::default().fg(Color::Cyan)),
            Span::raw(idle.hook_count.to_string()),
        ]),
        Line::from(vec![
            Span::styled("Agents: ", Style::default().fg(Color::Cyan)),
            Span::raw(idle.agent_count.to_string()),
        ]),
        Line::from(vec![
            Span::styled("Skills: ", Style::default().fg(Color::Cyan)),
            Span::raw(idle.skill_count.to_string()),
        ]),
        Line::from(""),
        Line::from(Span::styled(
            "Suggested: run /orchestrate to start a job",
            Style::default().fg(Color::DarkGray),
        )),
    ];
    let sys = Paragraph::new(sys_lines)
        .block(Block::default().title(" System Status ").borders(Borders::ALL));
    f.render_widget(sys, content_chunks[1]);

    // Footer
    let footer = Paragraph::new(Line::from(vec![
        Span::styled(" q", Style::default().fg(Color::Yellow)),
        Span::raw(": quit"),
    ]))
    .block(Block::default().borders(Borders::ALL));
    f.render_widget(footer, chunks[2]);
}

fn render_active(f: &mut Frame, app: &App) {
    let area = f.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(0),
            Constraint::Length(3),
        ])
        .split(area);

    // Header with job ID and task summary
    let job_id = app
        .job_tabs
        .get(app.selected_tab)
        .cloned()
        .unwrap_or_default();
    let task_snippet = app
        .active_job
        .as_ref()
        .map(|j| truncate(&j.task_line, 50))
        .unwrap_or_default();
    let verdict_snippet = app
        .active_job
        .as_ref()
        .filter(|j| !j.verdict.is_empty())
        .map(|j| format!(" | verdict: {}", truncate(&j.verdict, 40)))
        .unwrap_or_default();
    let done_count = app
        .active_job
        .as_ref()
        .map(|j| j.criteria.iter().filter(|(done, _)| *done).count())
        .unwrap_or(0);
    let total_count = app
        .active_job
        .as_ref()
        .map(|j| j.criteria.len())
        .unwrap_or(0);
    let mut header_spans = vec![
        Span::styled(" caf-hud ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
        Span::styled("| active: ", Style::default().fg(Color::Green)),
        Span::styled(job_id.clone(), Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
    ];
    if !task_snippet.is_empty() {
        header_spans.push(Span::styled(" — ", Style::default().fg(Color::DarkGray)));
        header_spans.push(Span::raw(task_snippet));
    }
    if total_count > 0 {
        header_spans.push(Span::styled(
            format!(" [{}/{}]", done_count, total_count),
            Style::default().fg(Color::Yellow),
        ));
    }
    if !verdict_snippet.is_empty() {
        header_spans.push(Span::styled(verdict_snippet, Style::default().fg(Color::Magenta)));
    }
    let header = Paragraph::new(Line::from(header_spans))
        .block(Block::default().borders(Borders::ALL));
    f.render_widget(header, chunks[0]);

    // Main split: left panel + right tabs
    let main_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(65), Constraint::Percentage(35)])
        .split(chunks[1]);

    render_left_panel(f, app, main_chunks[0]);
    render_right_panel(f, app, main_chunks[1]);

    // Footer
    let footer = Paragraph::new(Line::from(vec![
        Span::styled(" q", Style::default().fg(Color::Yellow)),
        Span::raw(": quit  "),
        Span::styled("←→", Style::default().fg(Color::Yellow)),
        Span::raw(": switch job  "),
        Span::styled("1-9", Style::default().fg(Color::Yellow)),
        Span::raw(": jump to job"),
    ]))
    .block(Block::default().borders(Borders::ALL));
    f.render_widget(footer, chunks[2]);
}

fn render_left_panel(f: &mut Frame, app: &App, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(12), // lead statuses
            Constraint::Min(8),     // working memory
            Constraint::Length(8),  // pending questions
        ])
        .split(area);

    // Lead statuses
    if let Some(job) = &app.active_job {
        let status_items: Vec<ListItem> = job
            .lead_statuses
            .iter()
            .map(|ls| {
                let (icon, color) = status_style(&ls.status);
                ListItem::new(Line::from(vec![
                    Span::styled(format!(" {} ", icon), Style::default().fg(color)),
                    Span::raw(format!("{:<20}", ls.role)),
                    Span::styled(ls.status.clone(), Style::default().fg(color)),
                ]))
            })
            .collect();
        let status_title = format!(" Lead Statuses — {} ", truncate(&job.orch_id, 20));
        let status_list = List::new(status_items)
            .block(Block::default().title(status_title).borders(Borders::ALL));
        f.render_widget(status_list, chunks[0]);

        // Working memory (last 5)
        let mem_items: Vec<ListItem> = job
            .working_memory
            .iter()
            .map(|entry| {
                // Show short timestamp (HH:MM) if available
                let ts_short = if entry.ts.len() >= 16 {
                    entry.ts[11..16].to_string()
                } else {
                    entry.ts.clone()
                };
                let ts_prefix = if !ts_short.is_empty() {
                    format!("{} ", ts_short)
                } else {
                    String::new()
                };
                let mut spans = vec![
                    Span::styled(ts_prefix, Style::default().fg(Color::DarkGray)),
                    Span::styled(
                        format!("[{}] ", truncate(&entry.lead, 16)),
                        Style::default().fg(Color::Cyan),
                    ),
                    Span::raw(truncate(&entry.summary, 55)),
                ];
                if !entry.why.is_empty() {
                    spans.push(Span::styled(
                        format!(" ({})", truncate(&entry.why, 28)),
                        Style::default().fg(Color::DarkGray),
                    ));
                }
                ListItem::new(Line::from(spans))
            })
            .collect();
        let mem_list = List::new(mem_items)
            .block(Block::default().title(" Working Memory (last 5) ").borders(Borders::ALL));
        f.render_widget(mem_list, chunks[1]);

        // Pending questions
        let q_items: Vec<ListItem> = job
            .pending_questions
            .iter()
            .map(|q| {
                let color = if q.critical { Color::Red } else { Color::Yellow };
                ListItem::new(Line::from(vec![
                    Span::styled(
                        format!("[{}] ", q.id),
                        Style::default().fg(Color::DarkGray),
                    ),
                    Span::styled(
                        format!("{}: ", q.lead),
                        Style::default().fg(color),
                    ),
                    Span::raw(q.question.clone()),
                ]))
            })
            .collect();
        let q_list = List::new(q_items)
            .block(
                Block::default()
                    .title(" Pending Questions ")
                    .borders(Borders::ALL),
            );
        f.render_widget(q_list, chunks[2]);
    } else {
        let empty = Paragraph::new("Loading...")
            .block(Block::default().title(" Lead Info ").borders(Borders::ALL));
        f.render_widget(empty, area);
    }
}

fn render_right_panel(f: &mut Frame, app: &App, area: Rect) {
    // Tabs list: job tabs newest-first
    let tab_items: Vec<ListItem> = app
        .job_tabs
        .iter()
        .enumerate()
        .map(|(i, id)| {
            let selected = i == app.selected_tab;
            let style = if selected {
                Style::default()
                    .fg(Color::Black)
                    .bg(Color::Cyan)
                    .add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(Color::White)
            };
            let prefix = if i < 9 {
                format!(" {} ", i + 1)
            } else {
                "   ".to_string()
            };
            ListItem::new(Line::from(vec![
                Span::styled(prefix, style),
                Span::styled(truncate(id, 24), style),
            ]))
        })
        .collect();

    let mut list_state = app.tab_list_state.clone();
    let tab_list = List::new(tab_items)
        .block(Block::default().title(" Jobs (newest first) ").borders(Borders::ALL))
        .highlight_style(Style::default().bg(Color::Cyan).fg(Color::Black));
    f.render_stateful_widget(tab_list, area, &mut list_state);
}

fn status_style(status: &str) -> (&'static str, Color) {
    match status {
        "running" => ("►", Color::Green),
        "done" => ("✓", Color::Blue),
        "failed" => ("✗", Color::Red),
        "aborted" => ("⊘", Color::Magenta),
        "pending" => ("·", Color::DarkGray),
        _ => ("?", Color::DarkGray),
    }
}

fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max {
        s.to_string()
    } else {
        let t: String = s.chars().take(max.saturating_sub(1)).collect();
        format!("{}…", t)
    }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

fn main() -> io::Result<()> {
    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let mut app = App::new();
    app.load_idle_summary();
    app.poll(); // Initial poll

    let tick_rate = Duration::from_millis(250);
    let mut last_tick = Instant::now();

    loop {
        terminal.draw(|f| render(f, &app))?;

        let timeout = tick_rate
            .checked_sub(last_tick.elapsed())
            .unwrap_or_else(|| Duration::from_secs(0));

        if event::poll(timeout)? {
            if let Event::Key(key) = event::read()? {
                if key.kind == KeyEventKind::Press {
                    match key.code {
                        KeyCode::Char('q') | KeyCode::Char('Q') => {
                            app.should_quit = true;
                        }
                        KeyCode::Left => app.prev_tab(),
                        KeyCode::Right => app.next_tab(),
                        KeyCode::Char('h') => app.prev_tab(),
                        KeyCode::Char('l') => app.next_tab(),
                        KeyCode::Char('1') => app.select_tab_by_number(1),
                        KeyCode::Char('2') => app.select_tab_by_number(2),
                        KeyCode::Char('3') => app.select_tab_by_number(3),
                        KeyCode::Char('4') => app.select_tab_by_number(4),
                        KeyCode::Char('5') => app.select_tab_by_number(5),
                        KeyCode::Char('6') => app.select_tab_by_number(6),
                        KeyCode::Char('7') => app.select_tab_by_number(7),
                        KeyCode::Char('8') => app.select_tab_by_number(8),
                        KeyCode::Char('9') => app.select_tab_by_number(9),
                        _ => {}
                    }
                }
            }
        }

        if last_tick.elapsed() >= tick_rate {
            app.poll();
            last_tick = Instant::now();
        }

        if app.should_quit {
            break;
        }
    }

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    Ok(())
}
