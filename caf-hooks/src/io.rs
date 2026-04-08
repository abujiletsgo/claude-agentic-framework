use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Write};
use std::path::Path;

use serde::Serialize;
use serde_json::Value;

use crate::types::HookInput;

/// Read all of stdin and parse as JSON into HookInput.
/// On any parse error, falls back to HookInput::Generic(Value::Null) — fail-open.
pub fn read_stdin() -> HookInput {
    let mut buf = String::new();
    if io::stdin().read_to_string(&mut buf).is_err() {
        return HookInput::Generic(Value::Null);
    }
    if buf.trim().is_empty() {
        return HookInput::Generic(Value::Object(Default::default()));
    }
    serde_json::from_str(&buf).unwrap_or_else(|_| {
        // Try to parse as generic Value so we can still access fields
        let v: Value = serde_json::from_str(&buf).unwrap_or(Value::Null);
        HookInput::Generic(v)
    })
}

/// Read stdin as a raw serde_json::Value (bypasses the HookInput enum).
/// Useful when the exact variant isn't needed.
pub fn read_stdin_value() -> Value {
    let mut buf = String::new();
    if io::stdin().read_to_string(&mut buf).is_err() {
        return Value::Null;
    }
    if buf.trim().is_empty() {
        return Value::Object(Default::default());
    }
    serde_json::from_str(&buf).unwrap_or(Value::Null)
}

/// Serialize output to JSON and print to stdout.
pub fn write_output<T: Serialize>(output: &T) {
    if let Ok(json) = serde_json::to_string(output) {
        println!("{}", json);
    }
}

/// Append a JSON record as a JSONL line to `path`.
/// Creates parent directories if they don't exist.
/// Returns Ok(()) even if the write fails (fail-open).
pub fn append_jsonl<T: Serialize>(path: &Path, record: &T) -> io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let line = serde_json::to_string(record).map_err(|e| io::Error::new(io::ErrorKind::Other, e))?;
    let mut file = OpenOptions::new().create(true).append(true).open(path)?;
    writeln!(file, "{}", line)?;
    Ok(())
}

/// Atomically write `content` to `path` using a temp file + rename.
/// Creates parent directories if they don't exist.
pub fn atomic_write(path: &Path, content: &str) -> io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let dir = path.parent().unwrap_or(Path::new("."));
    // Write to a temp file first
    let tmp_path = dir.join(format!(
        ".tmp_{}_{}",
        path.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("file"),
        std::process::id()
    ));
    {
        let mut tmp = File::create(&tmp_path)?;
        tmp.write_all(content.as_bytes())?;
        tmp.flush()?;
    }
    // Atomic rename
    fs::rename(&tmp_path, path)?;
    Ok(())
}

/// Silently append JSONL, ignoring errors (for fire-and-forget hooks).
pub fn try_append_jsonl<T: Serialize>(path: &Path, record: &T) {
    let _ = append_jsonl(path, record);
}
