# slog - SLURM Log Viewer

A Python utility for viewing SLURM job logs with color-coded output, live following, and flexible job identification.

## Installation

### 1. Download the Script

```bash
# Clone the repository or download the script directly
git clone https://github.com/danielhmendoza01/slog.git
cd slog

# Or download just the script
wget https://raw.githubusercontent.com/danielhmendoza01/slog/main/slog.py
# Or use curl
curl -O https://raw.githubusercontent.com/danielhmendoza01/slog/main/slog.py
```

### 2. Configure slog

Create a configuration file for slog:

```bash
# Create config directory
mkdir -p ~/.config/slog

# Copy the example configuration
cp slog.conf.example ~/.config/slog/slog.conf

# Edit the configuration with your SLURM log paths
vim ~/.config/slog/slog.conf
```

Update the paths in the configuration file to match your SLURM setup:
```ini
[paths]
logs_out_dir = /path/to/your/slurm/output/logs
logs_err_dir = /path/to/your/slurm/error/logs
```
```slog``` works best if you put all your SLURM logs for every run to go to one folder for out and another for error.

### 3. Set Up Local Bin Directory

```bash
# Create local bin directory if it doesn't exist
mkdir -p ~/.local/bin

# Copy the script to your local bin
cp slog.py ~/.local/bin/

# Make it executable
chmod +x ~/.local/bin/slog.py
```

### 4. Create Wrapper Script

Create a wrapper script to use `slog` as a command:

```bash
# Create the wrapper
cat > ~/.local/bin/slog << 'EOF'
#!/bin/bash
exec python3 ~/.local/bin/slog.py "$@"
EOF

# Make the wrapper executable
chmod +x ~/.local/bin/slog
```

### 5. Update Your PATH

Add `~/.local/bin` to your PATH if it's not already there:

```bash
# Add to your shell configuration file (~/.bashrc, ~/.zshrc, etc.)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Reload your shell configuration
source ~/.bashrc
```

### Alternative Installation Methods

#### Using Symbolic Links

If you prefer to keep the script in the cloned repository and use a symbolic link:

```bash
# Create symbolic link instead of copying
ln -s /path/to/slog/repo/slog.py ~/.local/bin/slog.py

# Create wrapper for the symlink
cat > ~/.local/bin/slog << 'EOF'
#!/bin/bash
exec python3 ~/.local/bin/slog.py "$@"
EOF
chmod +x ~/.local/bin/slog
```

## Configuration

slog looks for configuration files in the following locations (in order):

1. `~/.config/slog/slog.conf` (recommended)
2. `~/.slog.conf`
3. `/etc/slog/slog.conf` (system-wide)
4. `slog.conf` in the same directory as the script

The configuration file uses INI format:

```ini
[paths]
logs_out_dir = /path/to/slurm/output/logs
logs_err_dir = /path/to/slurm/error/logs
```

Paths can use `~` for home directory expansion.

## Usage

After installation, you can use `slog` from anywhere:

```bash
# View logs by job ID
slog 12345

# View logs by job name
slog myjob

# View logs by job_name-job_id format
slog myjob-12345

# View both output and error logs
slog -b 12345

# Follow logs in real-time
slog -f myjob

# Watch job and show logs when complete
slog -w running_job

# Disable color output
slog --no-color 12345

# View only error logs
slog -e 12345
```

## Options

- `-f, --follow`: Follow log output in real-time
- `-e, --error`: Show only error log
- `-b, --both`: Show both output and error logs
- `-w, --watch`: Watch job status and show logs when complete
- `--no-color`: Disable colored output

## Requirements

- Python 3.6+
- SLURM environment with `squeue` command (for watch mode)
- Standard Unix utilities: `less`, `tail`

## Features

- **Smart Job Resolution**: Accepts job IDs, job names, or combined formats
- **Color-Coded Output**: Different colors for timestamps, warnings, errors
- **Live Following**: Real-time log monitoring with `-f` option
- **Job Watching**: Wait for job completion with `-w` option
- **Flexible Display**: Show output, error, or both logs
- **Intelligent Paging**: Uses `less` with color support when appropriate

## Troubleshooting

1. **Command not found**: Ensure `~/.local/bin` is in your PATH
2. **No logs found**: Check that the log directories in the script match your SLURM configuration
3. **Permission denied**: Make sure both `slog.py` and `slog` are executable (`chmod +x`)
4. **Python not found**: Ensure Python 3 is installed and available as `python3`

## Uninstallation

To remove slog:

```bash
rm ~/.local/bin/slog ~/.local/bin/slog.py
```
