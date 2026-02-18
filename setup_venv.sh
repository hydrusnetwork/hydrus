#!/bin/bash

# Minimal setup script - finds Python and delegates to tools/setup_venv.py

script_dir="$(cd "$(dirname "$0")" && pwd)" || exit 1

py_command=python3

if ! type -P $py_command >/dev/null 2>&1; then
    echo "No 'python3' found, trying 'python'..."
    py_command=python
fi

if ! type -P $py_command >/dev/null 2>&1; then
    echo "ERROR: Could not find python3 or python!"
    exit 1
fi

# Delegate to Python setup script
exec "$py_command" "$script_dir/setup_venv.py"
