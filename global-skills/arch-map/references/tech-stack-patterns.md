# Tech Stack Adaptation Notes

The dependency scanning commands differ by stack. Adapt Phase 2 accordingly:

**Python projects:**
- Read patterns: `open(`, `json.load(`, `pd.read_`, `sqlite3.connect`, `pickle.load`, `Path(..).read_text`
- Write patterns: `json.dump(`, `pickle.dump(`, `.write_text(`, `open(.*, 'w')`
- Import patterns: `from mypackage.` or `import mypackage.`

**Node/TypeScript projects:**
- Read patterns: `fs.readFile`, `require(`, `import ... from`, `fetch(`, `axios.get`
- Write patterns: `fs.writeFile`, `writeFileSync`, `res.json(`, `db.insert`
- Config files: `package.json` scripts section shows entry points

**Rust projects:**
- Read patterns: `std::fs::read`, `serde_json::from_str`, `File::open`
- Write patterns: `std::fs::write`, `serde_json::to_string`, `File::create`
- Module graph: `Cargo.toml` `[dependencies]` + `mod` declarations in `lib.rs`/`main.rs`

**Go projects:**
- Read patterns: `os.Open`, `json.Unmarshal`, `ioutil.ReadFile`
- Write patterns: `os.Create`, `json.Marshal`, `ioutil.WriteFile`

**Mixed stacks (Python + Rust/Go/Node):**
- Map each language's modules separately in their own subgraph
- Show the FFI/bridge boundary explicitly (e.g. PyO3, CGo, WASM)
- Note serialization format at the boundary (JSON, protobuf, etc.)

---

## Examples

### Example 1: Data Science / ML Project
User: "Map out how this project works"

Layers found: `data/` (raw CSVs, processed PKL) → `src/preprocessing/` → `src/models/` → `notebooks/` → `scripts/train.py` → `artifacts/` → `app/`

Diagram shows: raw data → preprocess → train → save model → serve

### Example 2: Web App (Next.js + Python API)
User: "What breaks if I change the auth module?"

Layers: `prisma/schema` → `lib/db.ts` → `api/routes/` → `pages/` + `components/`

Quick Reference shows: "Changed `lib/auth.ts` → affects: `api/routes/protected/*.ts` (8 files), `middleware.ts`, `components/AuthGuard.tsx`"

### Example 3: CLI Tool with Plugins
User: "/arch-map"

Maps plugin interface → core CLI → plugin directory → config file → output formatters

Duplication warning: "Plugin interface defined in `src/types.ts` AND `docs/plugin-api.md` — keep in sync"
