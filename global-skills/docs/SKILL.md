---
name: docs
version: 1.0.0
description: "Smart Office document skill — create, read, and edit Word (.docx), Excel (.xlsx), and PowerPoint (.pptx) files via OfficeCLI MCP. Trigger when user mentions any Office document task: 'edit the spreadsheet', 'update the slide deck', 'create a report', 'add a chart', 'format the document'. Chains with /solve and /orchestrate for complex multi-document workflows."
user-invocable: true
---

# Office Document Skill (`/docs`)

Routes all Word/Excel/PowerPoint tasks through the **OfficeCLI MCP server** — no Python libraries, no Office installation needed. Works anywhere CAF runs. Integrates naturally with `/solve`, `/orchestrate`, and `/research`.

## When This Skill Fires

Trigger automatically when the user mentions:
- File extensions: `.docx`, `.xlsx`, `.pptx`, `.doc`, `.xls`, `.ppt`
- Apps: Word, Excel, PowerPoint, spreadsheet, slide deck, presentation, workbook
- Actions: "edit the report", "update the chart", "create a document", "format the table", "add a slide", "fill in the template", "generate a summary doc"

Also fires on `/docs` slash command.

---

## Tool Surface (via MCP)

OfficeCLI is registered as an MCP server named `officecli`. All commands are available as MCP tool calls — no Bash needed.

### Three-Layer Model (escalate as needed)

**L1 — Read & Inspect** (start here)
```
officecli view <file> --mode outline     # document structure
officecli view <file> --mode text        # plain text dump
officecli view <file> --mode stats       # word count, slide count, cell count
officecli view <file> --mode html        # rendered HTML preview
officecli view <file> --mode issues      # validation problems
```

**L2 — DOM Operations** (most tasks live here)
```
officecli get  <file> <path>              # read element: /body/p[3], /slide[1]/shape[2]
officecli set  <file> <path> <prop> <val> # modify: text, font, color, size, bold, italic
officecli add  <file> <path> <type>       # insert paragraph, row, slide, shape, chart
officecli remove <file> <path>            # delete element
officecli move   <file> <path> --index N  # reorder (0-based index)
officecli query  <file> "run:contains(TODO)" # CSS-like selectors
officecli batch  <file> < ops.json        # multiple ops in one open/save cycle
```

**L3 — Raw XML** (only when L2 can't do it)
```
officecli raw     <file> <xpath>          # read raw OpenXML
officecli raw-set <file> <xpath> <value>  # write raw XML
```

### Other Commands
```
officecli create  <file.docx|xlsx|pptx>  # blank document
officecli merge   <template> <data.json> # template variable substitution
officecli validate <file>                 # OpenXML schema check
officecli open    <file>                  # resident mode: keep in memory (fast multi-step)
officecli close   <file>                  # release from memory
```

### Path Conventions
- **1-based** XPath: `/body/p[3]` = third paragraph, `/slide[2]/shape[1]` = first shape on slide 2
- `--index` for ordering is **0-based** (array convention — documented difference)
- Colors: `FF0000`, `red`, `rgb(255,0,0)` — all accepted
- Sizes: `12pt`, `0.5cm`, `150%`, `914400` (EMUs) — all accepted

---

## Execution Protocol

### Step 1: Understand the file first
Always run `view --mode outline` or `view --mode stats` before editing. Never guess structure.

### Step 2: Choose the right layer
- Reading content → L1
- Editing text, formatting, adding rows/slides → L2
- Complex XML manipulation → L3

### Step 3: Use resident mode for multi-step edits
```
officecli open report.docx     # load once
officecli set report.docx /body/p[1] text "New Title"
officecli add report.docx /body table --rows 5 --cols 3
officecli close report.docx    # flush to disk
```

### Step 4: Validate after edits
```
officecli validate <file>      # catch OpenXML schema errors before delivery
```

---

## Chaining with Other CAF Skills

### With `/solve` — autonomous document debugging
```
User: "The chart in report.xlsx is showing wrong data"
→ /docs inspects via officecli view --mode issues
→ /solve takes the findings and iterates fixes autonomously
```

Invoke pattern:
```
Agent(subagent_type="builder", model="sonnet", prompt="Fix chart data in report.xlsx. 
Inspection output: <paste officecli view output here>. 
Use officecli MCP tools to read and correct the chart data source.")
```

### With `/orchestrate` — parallel multi-document work
```
User: "Update all 12 regional reports with Q1 actuals from the master spreadsheet"
→ /orchestrate spawns parallel agents, one per report
→ Each agent uses officecli to read master.xlsx and write to its regional report
```

Invoke pattern:
```
Use the orchestrator agent. Task: update regional reports in parallel.
Each sub-agent should: 
1. officecli view master.xlsx to find Q1 actuals
2. officecli set regional_XX.xlsx to update figures
3. officecli validate regional_XX.xlsx
```

### With `/research` — build documents from research
```
User: "Research the top 5 AI frameworks and put it in a slide deck"
→ /research gathers data
→ /docs creates presentation.pptx and populates slides
```

### With `/solve` + `/orchestrate` together — complex document assembly
```
User: "Create a monthly report: pull data from sales.xlsx, generate charts, 
       write the executive summary in Word, and add slides for each region"
→ Caddy classifies as multi_step → /orchestrate
→ Orchestrator spawns: data-agent (read xlsx), chart-agent (add charts), 
  writer-agent (compose docx), slides-agent (build pptx)
→ Each agent uses officecli MCP tools
→ /solve handles any failures or data mismatches
```

---

## Quick Examples

### Create and populate a Word doc
```
officecli create report.docx
officecli add report.docx /body paragraph --text "Executive Summary"
officecli set report.docx /body/p[1] bold true
officecli set report.docx /body/p[1] font-size 18pt
officecli add report.docx /body paragraph --text "Q1 revenue exceeded target by 12%."
officecli validate report.docx
```

### Read and update an Excel spreadsheet
```
officecli view sales.xlsx --mode outline
officecli get  sales.xlsx /sheet[1]/row[2]/cell[3]
officecli set  sales.xlsx /sheet[1]/row[2]/cell[3] value 142500
officecli add  sales.xlsx /sheet[1] row --after 10
```

### Build a PowerPoint slide deck from a template
```
officecli create deck.pptx
officecli merge template.pptx data.json --out deck.pptx
officecli view deck.pptx --mode outline
officecli add deck.pptx /slide[1] shape --type chart --data chart_data.json
```

### Batch operations (one file open/save cycle)
```json
[
  {"op": "set", "path": "/body/p[1]", "prop": "text", "value": "Updated Title"},
  {"op": "set", "path": "/body/p[1]", "prop": "bold", "value": "true"},
  {"op": "add", "path": "/body", "type": "paragraph", "text": "New paragraph after title"}
]
```
```bash
officecli batch report.docx < ops.json
```

---

## Error Recovery

All commands return structured JSON with `--json` flag. Error codes:
- `not_found` — path doesn't exist; run `view --mode outline` to find correct path
- `invalid_value` — bad format; check color/size/dimension conventions above
- `unsupported_property` — escalate to L3 raw access

When errors occur, re-read the structure with `view --mode outline` before retrying. Do not guess paths.

---

## Performance Notes

- **Single edit**: direct `officecli set/add/remove` call
- **5+ edits to same file**: use `officecli open` (resident mode) — document stays in memory, near-zero per-operation latency, 12-min idle watchdog
- **Parallel multi-file**: spawn separate agents, each with its own resident session
