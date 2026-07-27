import sys
import re
import os
import uuid
import tempfile
import subprocess
from pathlib import Path
from typing import Callable, Optional

from agent.llm_client import get_model

def run_generated_code(description: str, speak: Optional[Callable] = None) -> str:
    if speak:
        speak("Writing custom code for this task, sir.")

    system_instruction = (
        "You are an expert Python developer. "
        "Write clean, complete, working Python code. "
        "Use standard library + common packages. "
        "Install missing packages with subprocess + pip if needed. "
        "Return ONLY the Python code. No explanation, no markdown, no backticks."
    )
    model = get_model(model_name="gemini-2.5-flash", system_instruction=system_instruction)

    try:
        response = model.generate_content(
            f"Write Python code to accomplish this task:\n\n{description}"
        )
        code = response.text.strip()
        code = re.sub(r"```(?:python)?", "", code).strip().rstrip("`").strip()

        tmp_dir = Path(tempfile.gettempdir())
        script_path = tmp_dir / f"temp_{uuid.uuid4().hex[:8]}.py"
        script_path.write_text(code, encoding="utf-8")

        print(f"[Executor] 🐍 Running generated code: {script_path}")

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["CAPTAIN_SANDBOX"] = "1"

        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True,
            timeout=120, cwd=str(Path.home()),
            env=env
        )

        try:
            script_path.unlink()
        except Exception:
            pass

        output = result.stdout.strip()
        error  = result.stderr.strip()

        if result.returncode == 0 and output:
            return output
        elif result.returncode == 0:
            return "Task completed successfully."
        elif error:
            raise RuntimeError(f"Code error: {error[:400]}")
        return "Completed."

    except subprocess.TimeoutExpired:
        raise RuntimeError("Generated code timed out after 120 seconds.")
    except Exception as e:
        raise RuntimeError(f"Generated code failed: {e}")
