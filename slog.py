#!/usr/bin/env python3

"""
SLURM Log Viewer - Python version
Place in ~/.local/bin/slog.py and make executable
Usage: slog.py [job_id] [options]
"""

import argparse
import configparser
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple, List

def load_config():
    """Load configuration from file."""
    config = configparser.ConfigParser()
    
    # Look for config file in multiple locations
    config_locations = [
        Path.home() / '.config' / 'slog' / 'slog.conf',
        Path.home() / '.slog.conf',
        Path('/etc/slog/slog.conf'),
        Path(__file__).parent / 'slog.conf'
    ]
    
    config_found = False
    for config_path in config_locations:
        if config_path.exists():
            try:
                config.read(config_path)
                config_found = True
                break
            except Exception as e:
                print(f"Warning: Failed to read config from {config_path}: {e}", file=sys.stderr)
    
    if not config_found:
        print("Error: No configuration file found. Please create one of the following:", file=sys.stderr)
        for path in config_locations:
            print(f"  - {path}", file=sys.stderr)
        print("\nExample configuration file available at: slog.conf.example", file=sys.stderr)
        sys.exit(1)
    
    # Read configuration values
    try:
        logs_out_dir = os.path.expanduser(config.get('paths', 'logs_out_dir'))
        logs_err_dir = os.path.expanduser(config.get('paths', 'logs_err_dir'))
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        print(f"Error: Invalid configuration file - {e}", file=sys.stderr)
        print("Please check your configuration file format.", file=sys.stderr)
        sys.exit(1)
    
    return logs_out_dir, logs_err_dir

# Load configuration
LOGS_OUT_DIR, LOGS_ERR_DIR = load_config()

# Color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

class SlogViewer:
    def __init__(self, no_color: bool = False):
        self.no_color = no_color or not sys.stdout.isatty()
        self.out_file = ""
        self.err_file = ""
    
    def colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if self.no_color:
            return text
        return f"{color}{text}{Colors.NC}"
    
    def list_recent_logs(self) -> None:
        """List recent log files."""
        print(self.colorize("Recent log files:", Colors.BOLD))
        print(self.colorize("=== Output logs ===", Colors.GREEN))
        
        try:
            out_files = list(Path(LOGS_OUT_DIR).glob("*.out"))
            out_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for f in out_files[:10]:
                stat = f.stat()
                size = stat.st_size
                mtime = time.strftime("%b %d %H:%M", time.localtime(stat.st_mtime))
                print(self.colorize(f"{mtime} {size:>8} {f.name}", Colors.CYAN))
        except (OSError, FileNotFoundError):
            pass
        
        print()
        print(self.colorize("=== Error logs ===", Colors.RED))
        
        try:
            err_files = list(Path(LOGS_ERR_DIR).glob("*.err"))
            err_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for f in err_files[:10]:
                stat = f.stat()
                size = stat.st_size
                mtime = time.strftime("%b %d %H:%M", time.localtime(stat.st_mtime))
                print(self.colorize(f"{mtime} {size:>8} {f.name}", Colors.CYAN))
        except (OSError, FileNotFoundError):
            pass
    
    def find_log_files(self, job_input: str) -> bool:
        """Find log files based on job input."""
        job_name = ""
        job_id = ""
        
        # Check if input is just a number (job ID)
        if job_input.isdigit():
            job_id = job_input
            # Try to find job name from existing log files
            try:
                out_files = list(Path(LOGS_OUT_DIR).glob(f"*-{job_id}.out"))
                if out_files:
                    job_name = out_files[0].stem.replace(f"-{job_id}", "")
            except (OSError, FileNotFoundError):
                pass
        else:
            # Input might be job_name or job_name-job_id
            match = re.match(r'^(.+)-(\d+)$', job_input)
            if match:
                job_name, job_id = match.groups()
            else:
                job_name = job_input
                # Find most recent job ID for this job name
                try:
                    pattern = f"{job_name}-*.out"
                    out_files = list(Path(LOGS_OUT_DIR).glob(pattern))
                    if out_files:
                        # Sort by version (natural sort for numbers)
                        out_files.sort(key=lambda x: [int(c) if c.isdigit() else c.lower() 
                                                    for c in re.split('([0-9]+)', str(x))])
                        latest = out_files[-1]
                        job_id = re.search(rf'{re.escape(job_name)}-(\d+)\.out$', str(latest))
                        if job_id:
                            job_id = job_id.group(1)
                except (OSError, FileNotFoundError):
                    pass
        
        if not job_name or not job_id:
            print(self.colorize(f"Error: Could not determine job name and ID from '{job_input}'", Colors.RED))
            return False
        
        self.out_file = f"{LOGS_OUT_DIR}/{job_name}-{job_id}.out"
        self.err_file = f"{LOGS_ERR_DIR}/{job_name}-{job_id}.err"
        
        job_info = f"Job: {self.colorize(job_name, Colors.YELLOW)} (ID: {self.colorize(job_id, Colors.CYAN)})"
        print(self.colorize(job_info, Colors.BOLD))
        return True
    
    def colorize_line(self, line: str, is_error: bool = False) -> str:
        """Apply contextual coloring to a line."""
        if self.no_color:
            return line
        
        # Preserve existing ANSI escape sequences
        if '\033[' in line:
            return line
        
        # Add contextual coloring for common patterns
        if is_error:
            # Error log coloring
            if re.search(r'[Ee]rror|ERROR|[Ff]ailed|FAILED', line):
                return self.colorize(line, Colors.RED)
            elif re.search(r'[Ww]arning|WARNING', line):
                return self.colorize(line, Colors.YELLOW)
            else:
                return self.colorize(line, Colors.MAGENTA)
        else:
            # Output log coloring
            if re.match(r'^[\+\>]', line):
                return self.colorize(line, Colors.GREEN)
            elif re.match(r'^[\-]', line):
                return self.colorize(line, Colors.RED)
            elif re.search(r'[Ss]uccess|SUCCESS|[Cc]ompleted|COMPLETED|[Dd]one|DONE', line):
                return self.colorize(line, Colors.GREEN)
            elif re.search(r'[Ee]rror|ERROR|[Ff]ailed|FAILED', line):
                return self.colorize(line, Colors.RED)
            elif re.search(r'[Ww]arning|WARNING', line):
                return self.colorize(line, Colors.YELLOW)
            elif re.match(r'^\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2}', line):
                return self.colorize(line, Colors.CYAN)
            elif re.match(r'^\[.*\]', line):
                return self.colorize(line, Colors.BLUE)
            else:
                return line
    
    def colorize_output(self, file_path: str, is_error: bool = False) -> None:
        """Display file with appropriate coloring."""
        if not os.path.exists(file_path):
            return
        
        # Use less with color support if available and output is to terminal
        if not self.no_color and sys.stdout.isatty() and os.system("command -v less >/dev/null 2>&1") == 0:
            env = os.environ.copy()
            env['LESS'] = '-R'
            subprocess.run(['less', file_path], env=env)
        else:
            # Cat with additional contextual coloring
            try:
                with open(file_path, 'r', errors='replace') as f:
                    for line in f:
                        line = line.rstrip('\n\r')
                        print(self.colorize_line(line, is_error))
            except (OSError, UnicodeDecodeError):
                print(self.colorize(f"Error reading file: {file_path}", Colors.RED))
    
    def follow_logs(self, out_file: str, err_file: str, show_out: bool, show_err: bool, status_interval: int = 10) -> None:
        """Follow log files with tail -f equivalent and job status monitoring."""
        files_to_follow = []
        if show_out and os.path.exists(out_file):
            files_to_follow.append(out_file)
        if show_err and os.path.exists(err_file):
            files_to_follow.append(err_file)
        
        if not files_to_follow:
            print(self.colorize("No log files found to follow", Colors.RED))
            return
        
        # Extract job ID from filename for status monitoring
        job_id_match = re.search(r'-(\d+)\.(out|err)$', files_to_follow[0])
        if not job_id_match:
            print(self.colorize("Warning: Could not extract job ID for status monitoring", Colors.YELLOW))
            job_id = None
        else:
            job_id = job_id_match.group(1)
        
        if len(files_to_follow) > 1:
            print(self.colorize("Following both output and error logs in real-time... (Ctrl+C to stop)", Colors.YELLOW))
            print(self.colorize(f"Output lines will be unmarked, error lines will have {self.colorize('[ERR]', Colors.RED)} prefix", Colors.CYAN))
            print()
        else:
            log_type = "output" if show_out else "error"
            print(self.colorize(f"Following {log_type} log... (Ctrl+C to stop)", Colors.YELLOW))
        
        try:
            import threading
            import queue
            import sys
            
            # Create queue for tail output
            output_queue = queue.Queue()
            
            # Use tail -f
            cmd = ['tail', '-f'] + files_to_follow
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, 
                                     universal_newlines=True, bufsize=1)
            
            # Thread to read tail output
            def read_output():
                for line in process.stdout:
                    output_queue.put(('log', line.rstrip('\n\r')))
                output_queue.put(('done', None))
            
            output_thread = threading.Thread(target=read_output)
            output_thread.daemon = True
            output_thread.start()
            
            # Thread to check job status
            job_running = True
            last_status = ""
            
            def check_job_status():
                nonlocal job_running, last_status
                while job_running:
                    if job_id:
                        result = subprocess.run(['squeue', '-j', job_id, '-h', '-o', '%T %M %R'], 
                                              capture_output=True, text=True)
                        if result.returncode == 0 and result.stdout.strip():
                            # Job is still running
                            status_parts = result.stdout.strip().split(None, 2)
                            state = status_parts[0] if len(status_parts) > 0 else "UNKNOWN"
                            runtime = status_parts[1] if len(status_parts) > 1 else "0:00"
                            reason = status_parts[2] if len(status_parts) > 2 else ""
                            
                            status = f"Job {job_id}: {state} - Runtime: {runtime}"
                            if reason and reason != "None":
                                status += f" - {reason}"
                            
                            if status != last_status:
                                output_queue.put(('status', status))
                                last_status = status
                        else:
                            # Job completed
                            job_running = False
                            output_queue.put(('completed', job_id))
                    
                    # Sleep for status_interval seconds unless job completed
                    for _ in range(status_interval * 10):  # Check every 0.1s for job completion
                        if not job_running:
                            break
                        time.sleep(0.1)
            
            if job_id:
                status_thread = threading.Thread(target=check_job_status)
                status_thread.daemon = True
                status_thread.start()
            
            # Main loop to display output
            current_status = ""
            log_lines = []
            max_lines = 50  # Keep last 50 lines in memory
            
            while True:
                try:
                    msg_type, content = output_queue.get(timeout=0.1)
                    
                    if msg_type == 'done':
                        break
                    elif msg_type == 'completed':
                        # Job completed, get final status
                        print("\n" + self.colorize("="*80, Colors.BOLD))
                        print(self.colorize(f"Job {content} completed!", Colors.GREEN + Colors.BOLD))
                        
                        # Try to get exit status from sacct if available
                        try:
                            result = subprocess.run(['sacct', '-j', content, '-n', '-X', '-o', 'State,ExitCode'], 
                                                  capture_output=True, text=True, timeout=5)
                            if result.returncode == 0 and result.stdout.strip():
                                state_info = result.stdout.strip().split()
                                if len(state_info) >= 2:
                                    state = state_info[0]
                                    exit_code = state_info[1]
                                    
                                    if state == "COMPLETED" and exit_code == "0:0":
                                        print(self.colorize(f"Status: {state} (Success)", Colors.GREEN + Colors.BOLD))
                                    elif state == "FAILED" or not exit_code.startswith("0:"):
                                        print(self.colorize(f"Status: {state} - Exit code: {exit_code}", Colors.RED + Colors.BOLD))
                                    else:
                                        print(self.colorize(f"Status: {state} - Exit code: {exit_code}", Colors.YELLOW + Colors.BOLD))
                            else:
                                print(self.colorize("Status: Job no longer in queue (sacct not available)", Colors.YELLOW))
                        except (subprocess.TimeoutExpired, FileNotFoundError):
                            print(self.colorize("Status: Job no longer in queue (sacct not available)", Colors.YELLOW))
                        
                        print(self.colorize("="*80, Colors.BOLD))
                        process.terminate()
                        return
                    elif msg_type == 'status':
                        current_status = content
                        # Reprint the status line
                        sys.stdout.write('\r' + ' ' * 80 + '\r')  # Clear line
                        sys.stdout.write(self.colorize(f"[{current_status}]", Colors.CYAN + Colors.BOLD))
                        sys.stdout.flush()
                    elif msg_type == 'log':
                        # Clear status line before printing log
                        if current_status:
                            sys.stdout.write('\r' + ' ' * 80 + '\r')
                            sys.stdout.flush()
                        
                        line = content
                        # Check if this is a tail header line (==> filename <==)
                        if re.match(r'^==>', line) and line.endswith('<=='):
                            if '.err' in line:
                                print(self.colorize(line, Colors.BOLD + Colors.RED))
                            else:
                                print(self.colorize(line, Colors.BOLD + Colors.GREEN))
                        else:
                            # Apply live coloring for regular content
                            if '\033[' in line:
                                print(line)
                            elif re.search(r'[Ss]uccess|SUCCESS|[Cc]ompleted|COMPLETED|[Dd]one|DONE', line):
                                print(self.colorize(line, Colors.GREEN))
                            elif re.search(r'[Ee]rror|ERROR|[Ff]ailed|FAILED', line):
                                print(self.colorize(line, Colors.RED))
                            elif re.search(r'[Ww]arning|WARNING', line):
                                print(self.colorize(line, Colors.YELLOW))
                            else:
                                print(line)
                        
                        # Reprint status line after log output
                        if current_status:
                            sys.stdout.write(self.colorize(f"[{current_status}]", Colors.CYAN + Colors.BOLD))
                            sys.stdout.flush()
                        
                except queue.Empty:
                    continue
                except KeyboardInterrupt:
                    raise
                        
        except KeyboardInterrupt:
            if process:
                process.terminate()
            print("\n" + self.colorize("Stopped following logs", Colors.YELLOW))
        except Exception as e:
            print(self.colorize(f"Error following logs: {e}", Colors.RED))
    
    def show_logs(self, show_out: bool = True, show_err: bool = True, follow: bool = False, status_interval: int = 10) -> None:
        """Display log files."""
        if follow:
            self.follow_logs(self.out_file, self.err_file, show_out, show_err, status_interval)
            return
        
        if show_out:
            if os.path.exists(self.out_file):
                header = f"=== OUTPUT LOG ({self.out_file}) ==="
                print(self.colorize(header, Colors.BOLD + Colors.GREEN))
                self.colorize_output(self.out_file, False)
            else:
                print(self.colorize(f"Output log not found: {self.out_file}", Colors.RED))
            print()
        
        if show_err:
            if os.path.exists(self.err_file):
                header = f"=== ERROR LOG ({self.err_file}) ==="
                print(self.colorize(header, Colors.BOLD + Colors.RED))
                self.colorize_output(self.err_file, True)
            else:
                print(self.colorize(f"Error log not found: {self.err_file}", Colors.RED))
    
    def show_last_job(self, status_interval: int = 10, **kwargs) -> None:
        """Show logs for the most recent job."""
        try:
            out_files = list(Path(LOGS_OUT_DIR).glob("*.out"))
            if not out_files:
                print(self.colorize("No log files found", Colors.RED))
                return
            
            # Get most recent file
            latest = max(out_files, key=lambda x: x.stat().st_mtime)
            last_job = latest.stem  # Remove .out extension
            
            print(self.colorize(f"Showing logs for most recent job: {last_job}", Colors.BOLD))
            print()
            
            if self.find_log_files(last_job):
                self.show_logs(status_interval=status_interval, **kwargs)
        except (OSError, FileNotFoundError):
            print(self.colorize("No log files found", Colors.RED))
    
    def watch_job(self, job_id: str, status_interval: int = 10, **kwargs) -> None:
        """Watch job status and show logs when complete."""
        if not job_id:
            print(self.colorize("Usage: slog watch <job_id>", Colors.RED))
            return
        
        print(self.colorize(f"Watching job {job_id}...", Colors.BOLD))
        
        try:
            while True:
                result = subprocess.run(['squeue', '-j', job_id], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    break
                time.sleep(10)
                print(self.colorize(".", Colors.YELLOW), end="", flush=True)
            
            print()
            print(self.colorize(f"Job {job_id} completed! Showing logs:", Colors.GREEN))
            print()
            
            if self.find_log_files(job_id):
                self.show_logs(status_interval=status_interval, **kwargs)
                
        except KeyboardInterrupt:
            print("\nStopped watching job")
        except Exception as e:
            print(self.colorize(f"Error watching job: {e}", Colors.RED))
    
    def show_job_status(self, job_id: str, status_interval: int = 10, **kwargs) -> None:
        """Show job status and logs."""
        if not job_id:
            print(self.colorize("Usage: slog status <job_id>", Colors.RED))
            return
        
        print(self.colorize("=== JOB STATUS ===", Colors.BOLD + Colors.BLUE))
        
        result = subprocess.run(['squeue', '-j', job_id], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(self.colorize(f"Job {job_id} not in queue (completed or doesn't exist)", Colors.YELLOW))
        
        print()
        print(self.colorize("=== LOGS ===", Colors.BOLD + Colors.BLUE))
        
        if self.find_log_files(job_id):
            self.show_logs(status_interval=status_interval, **kwargs)


def main():
    parser = argparse.ArgumentParser(
        description="SLURM Log Viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  slog.py 9560                    # Show both .out and .err for job 9560
  slog.py lodei-9560             # Same as above, using full job name
  slog.py 9560 -f               # Follow logs with live updates
  slog.py 9560 -f --status-interval 5  # Follow with 5-second status updates
  slog.py 9560 -e               # Show only error log
  slog.py last                  # Show logs for most recent job
  slog.py watch 9560            # Watch job and show logs when done
  slog.py status 9560           # Show job status + logs
  slog.py -l                    # List recent log files
        """
    )
    
    parser.add_argument('job_input', nargs='?', 
                       help='Job ID, job name, or command (last/watch/status)')
    parser.add_argument('-f', '--follow', action='store_true',
                       help='Follow log files (live updates with tail -f)')
    parser.add_argument('-e', '--error', action='store_true',
                       help='Show only error log')
    parser.add_argument('-o', '--out', action='store_true',
                       help='Show only output log')
    parser.add_argument('-l', '--list', action='store_true',
                       help='List recent log files')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    parser.add_argument('--status-interval', type=int, default=10,
                       help='Status update interval in seconds for -f mode (default: 10)')
    parser.add_argument('job_args', nargs='*',
                       help='Additional arguments for watch/status commands')
    
    args = parser.parse_args()
    
    if not args.job_input and not args.list:
        parser.print_help()
        sys.exit(1)
    
    viewer = SlogViewer(no_color=args.no_color)
    
    # Handle list command
    if args.list:
        viewer.list_recent_logs()
        return
    
    # Determine show options
    show_out = not args.error
    show_err = not args.out
    if args.error and args.out:
        show_out = show_err = True
    
    show_options = {
        'show_out': show_out,
        'show_err': show_err,
        'follow': args.follow,
        'status_interval': args.status_interval
    }
    
    # Handle special commands
    if args.job_input == 'last':
        viewer.show_last_job(**show_options)
    elif args.job_input == 'watch':
        if not args.job_args:
            print(viewer.colorize("Usage: slog.py watch <job_id>", Colors.RED))
            sys.exit(1)
        viewer.watch_job(args.job_args[0], **show_options)
    elif args.job_input == 'status':
        if not args.job_args:
            print(viewer.colorize("Usage: slog.py status <job_id>", Colors.RED))
            sys.exit(1)
        viewer.show_job_status(args.job_args[0], **show_options)
    else:
        # Regular job input
        if viewer.find_log_files(args.job_input):
            viewer.show_logs(**show_options)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()