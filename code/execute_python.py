def execute_python_code(code: str) -> str:
    """
    Execute a Python code string securely and return structured output.
    Output includes stdout, stderr, return code, and a success flag.
    """
    import subprocess, json, tempfile, os, sys
    script_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(code)
            script_path = f.name
        # Optionally print content of the script for debugging
        # with open(script_path, 'r') as f:
        #     print(f"Executing Python script:\n{f.read()}")

        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, errors='replace', timeout=10
        )
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
    return json.dumps(output)
