"""
executor.py — Runs multi-step agent plans with retry and replan logic.
"""
import time
import threading
from typing import Callable, Dict, Any, List

from utils.logger import log
from agent.planner import create_plan, replan
from agent.error_handler import analyze_error, generate_fix, ErrorDecision
from agent.tool_registry import call_tool
from agent.context_manager import inject_context
from agent.llm_client import get_model

# Retry delay: starts at 1s, doubles on each attempt (max 4s)
_RETRY_BASE_DELAY = 1.0
_RETRY_MAX_DELAY  = 4.0


class AgentExecutor:

    MAX_REPLAN_ATTEMPTS = 2

    def execute(
        self,
        goal:        str,
        speak:       Callable | None        = None,
        cancel_flag: threading.Event | None = None,
    ) -> str:
        log.info(f"[Executor] 🎯 Goal: {goal}")

        replan_attempts = 0
        completed_steps: List[Dict[str, Any]] = []
        step_results:    Dict[Any, Any]        = {}
        plan = create_plan(goal)

        while True:
            steps = plan.get("steps", [])
            if not steps:
                msg = "I couldn't create a valid plan for this task, sir."
                if speak:
                    speak(msg)
                return msg

            success      = True
            failed_step  = None
            failed_error = ""

            for step in steps:
                if cancel_flag and cancel_flag.is_set():
                    if speak:
                        speak("Task cancelled, sir.")
                    return "Task cancelled."

                step_num = step.get("step", "?")
                tool     = step.get("tool", "web_search")
                desc     = step.get("description", "")
                params   = step.get("parameters", {})

                params = inject_context(params, tool, step_results, goal=goal)
                log.info(f"[Executor] ▶️ Step {step_num}: [{tool}] {desc}")

                attempt   = 1
                step_ok   = False
                delay     = _RETRY_BASE_DELAY

                while attempt <= 3:
                    if cancel_flag and cancel_flag.is_set():
                        break
                    try:
                        result = call_tool(tool, params, speak)
                        step_results[step_num] = result
                        completed_steps.append(step)
                        log.info(f"[Executor] ✅ Step {step_num}: {str(result)[:100]}")
                        step_ok = True
                        break

                    except Exception as exc:
                        error_msg = str(exc)
                        log.warning(f"[Executor] ❌ Step {step_num} attempt {attempt}: {error_msg}")

                        recovery = analyze_error(step, error_msg, attempt=attempt)
                        decision = recovery["decision"]
                        user_msg = recovery.get("user_message", "")

                        if speak and user_msg:
                            speak(user_msg)

                        if decision == ErrorDecision.RETRY:
                            attempt += 1
                            time.sleep(min(delay, _RETRY_MAX_DELAY))  # exponential backoff
                            delay *= 2
                            continue

                        elif decision == ErrorDecision.SKIP:
                            log.info(f"[Executor] ⏭️ Skipping step {step_num}")
                            completed_steps.append(step)
                            step_ok = True
                            break

                        elif decision == ErrorDecision.ABORT:
                            msg = f"Task aborted, sir. {recovery.get('reason', '')}"
                            if speak:
                                speak(msg)
                            return msg

                        else:  # FIX
                            fix_suggestion = recovery.get("fix_suggestion", "")
                            if fix_suggestion and tool != "generated_code":
                                try:
                                    fixed_step = generate_fix(step, error_msg, fix_suggestion)
                                    if speak:
                                        speak("Trying an alternative approach, sir.")
                                    res = call_tool(
                                        fixed_step["tool"],
                                        fixed_step["parameters"],
                                        speak,
                                    )
                                    step_results[step_num] = res
                                    completed_steps.append(step)
                                    step_ok = True
                                    break
                                except Exception as fix_err:
                                    log.warning(f"[Executor] ⚠️ Fix failed: {fix_err}")

                            failed_step  = step
                            failed_error = error_msg
                            success      = False
                            break

                if not step_ok and not failed_step:
                    failed_step  = step
                    failed_error = "Max retries exceeded"
                    success      = False

                if not success:
                    break

            if success:
                return self._summarize(goal, completed_steps, speak)

            if replan_attempts >= self.MAX_REPLAN_ATTEMPTS:
                msg = f"Task failed after {replan_attempts} replan attempts, sir."
                if speak:
                    speak(msg)
                return msg

            if speak:
                speak("Adjusting my approach, sir.")
            replan_attempts += 1
            plan = replan(goal, completed_steps, failed_step, failed_error)

    def _summarize(self, goal: str, completed_steps: List[Dict[str, Any]],
                   speak: Callable | None) -> str:
        fallback = f"All done, sir. Completed {len(completed_steps)} steps for: {goal[:60]}."
        try:
            model     = get_model(model_name="gemini-2.5-flash-lite")
            steps_str = "\n".join(f"- {s.get('description', '')}" for s in completed_steps)
            prompt    = (
                f'User goal: "{goal}"\n'
                f"Completed steps:\n{steps_str}\n\n"
                "Write a single natural sentence summarising what was accomplished. "
                "Address the user as 'sir'. Be direct and positive."
            )
            response = model.generate_content(prompt)
            summary  = response.text.strip()
            if speak:
                speak(summary)
            return summary
        except Exception:
            if speak:
                speak(fallback)
            return fallback
