# Test Scaffolds by Framework

Ready-to-adapt boilerplate. Replace `my_function` / `MyFunction` / `myFunction` with the real symbol under test.

---

## Python (pytest)

```python
import pytest
from unittest.mock import Mock, patch

class TestMyFunction:
    def test_happy_path(self):
        result = my_function(valid_input)
        assert result == expected_output

    def test_edge_case_empty(self):
        with pytest.raises(ValueError):
            my_function("")

    @patch("module.external_service")
    def test_with_mock(self, mock_service):
        mock_service.return_value = "mocked"
        result = my_function(input)
        assert result == "expected"
```

---

## JavaScript / TypeScript (Jest / Vitest)

```typescript
describe("myFunction", () => {
  it("should handle normal input", () => {
    expect(myFunction(validInput)).toBe(expected);
  });

  it("should throw on invalid input", () => {
    expect(() => myFunction(null)).toThrow();
  });

  it("should call external service", async () => {
    vi.mock("./service");
    const result = await myFunction(input);
    expect(result).toMatchSnapshot();
  });
});
```

---

## Go (table-driven)

```go
func TestMyFunction(t *testing.T) {
    tests := []struct {
        name     string
        input    string
        expected string
        wantErr  bool
    }{
        {"happy path", "valid", "result", false},
        {"empty input", "", "", true},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := MyFunction(tt.input)
            if (err != nil) != tt.wantErr {
                t.Errorf("MyFunction() error = %v, wantErr %v", err, tt.wantErr)
            }
            if got != tt.expected {
                t.Errorf("MyFunction() = %v, want %v", got, tt.expected)
            }
        })
    }
}
```
