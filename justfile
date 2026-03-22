set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

# Run the room optimizer.
run:
    uv run room-optimizer

# Run all tests.
[windows]
test-all:
    fd tests | % { uv run pytest $_ }

# Run the type checker.
ty:
    uv run ty check packages

# Run the linter.
lint:
    uv run ruff check packages

# Run the linter with auto-fix.
fix:
    uv run ruff check packages --fix

# Format the code.
format:
    uv run ruff format packages
