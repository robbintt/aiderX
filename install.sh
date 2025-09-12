

export UV_VENV_CLEAR=1 # yes, clear. can also use --clear
uv venv
uv pip install .[dev]

# to activate, run this command as: ". ./install.sh"
. .venv/bin/activate

#uv pip install . --system
