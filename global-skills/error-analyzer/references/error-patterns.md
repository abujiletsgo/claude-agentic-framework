# Error Analyzer — Reference Patterns

## Error Category Table

| Category | Indicators | Priority |
|----------|-----------|----------|
| **Syntax** | SyntaxError, parse error, unexpected token | High (quick fix) |
| **Type** | TypeError, type mismatch, undefined is not | High |
| **Runtime** | NullPointerException, segfault, SIGABRT | Critical |
| **Import/Module** | ModuleNotFoundError, Cannot find module | Medium |
| **Network** | ECONNREFUSED, timeout, 404/500 | Medium |
| **Permission** | EACCES, PermissionError, 403 | Medium |
| **Configuration** | Missing env var, invalid config, YAML parse | Medium |
| **Resource** | OOM, disk full, too many open files | Critical |

## Common Error Patterns by Language

### Python
- `ModuleNotFoundError`: Check virtualenv activation, pip install
- `AttributeError: NoneType`: Trace back None propagation
- `KeyError`: Check dict key existence, use `.get()` with default
- `IndentationError`: Mixed tabs/spaces, copy-paste issues

### JavaScript/TypeScript
- `TypeError: Cannot read properties of undefined`: Optional chaining missing
- `ReferenceError`: Variable scoping, hoisting, import issues
- `SyntaxError: Unexpected token`: JSON parse failure, template literal issues
- `ENOENT`: File path issues, missing build artifacts

### Shell/Hooks (CAF-specific — skip in non-framework projects)
- Exit code 2: Hook blocked the operation (check patterns.yaml)
- `uv run` failures: Missing pyproject.toml, dependency issues
- JSON parse errors: Invalid stdin to hook scripts
- Permission denied: Missing chmod +x on scripts
