def execute_bash_command(command: str) -> str:
    """Execute a bash command and return the output."""
    import subprocess
    result = subprocess.run(['bash', '-c', command], capture_output=True, text=True, errors='replace')
    return result.stdout if result.returncode == 0 else result.stderr

