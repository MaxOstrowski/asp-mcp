def execute_bash_command(command: str) -> str:
    """ 
    Execute a bash command securely and return structured output.
    Bash scripts do not handle quotes and special characters very well, maybe use python for this.
    Output includes stdout, stderr, return code, and a success flag.
    """
    import subprocess, json, tempfile, os
    script_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as f:
            f.write(command)
            script_path = f.name       

        result = subprocess.run(['bash', script_path],
            capture_output=True, text=True, errors='replace', timeout=10)
        output = {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode,
            'success': result.returncode == 0
        }
    except subprocess.TimeoutExpired as te:
        output = {
            'stdout': te.stdout if hasattr(te, 'stdout') else '',
            'stderr': 'Timeout expired',
            'returncode': -1,
            'success': False
        }
    except Exception as e:
        output = {
            'stdout': '',
            'stderr': str(e),
            'returncode': -1,
            'success': False
        }
    finally:
        if script_path is not None and os.path.exists(script_path):
            os.unlink(script_path)
    try:
        return json.dumps(output, indent=2)
    except TypeError:
        # Fallback if json.dumps fails, return a simple string representation
        output['success'] = False
        output['stderr'] = 'Failed to serialize output to JSON'
        output['stdout'] = ""
        output['returncode'] = ""
    return json.dumps(output)

#def execute_bash_command(command: str) -> str:
#    """Execute a bash command and return the output."""
#    import subprocess
#    result = subprocess.run(['bash', '-c', command], capture_output=True, text=True, errors='replace')
#    return result.stdout if result.returncode == 0 else result.stderr

