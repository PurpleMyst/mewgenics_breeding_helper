set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

# Run the room optimizer.
run:
    uv run room-optimizer

# Run all tests.
[windows]
test-all:
    fd tests | % { uv run pytest $_ }
