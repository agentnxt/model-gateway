import os
import json
import datetime

class DeploymentLogger:
    def __init__(self, agent_id: str, log_dir: str = "logs"):
        self.agent_id = agent_id
        self.log_dir = os.path.join(log_dir, agent_id)
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.audit_log_file = os.path.join(self.log_dir, f"audit_{self.session_id}.log")
        self.deployment_log_file = os.path.join(self.log_dir, f"deployment_{self.session_id}.jsonl")

    def _log(self, file, message):
        with open(file, 'a') as f:
            f.write(f"{datetime.datetime.now().isoformat()} - {message}
")

    def audit(self, event_type: str, details: dict):
        """Logs a high-level audit event."""
        message = f"[{event_type.upper()}] {json.dumps(details)}"
        self._log(self.audit_log_file, message)
        print(f"[AUDIT] {message}") # Also print to console

    def deployment_step(self, step_name: str, status: str, details: dict):
        """Logs a structured deployment step."""
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "sessionId": self.session_id,
            "agentId": self.agent_id,
            "step": step_name,
            "status": status,
            "details": details
        }
        with open(self.deployment_log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '
')

    def error(self, step: str, error_message: str, details: dict = None):
        """Logs an error and can be extended to send to GlitchTip."""
        self.deployment_step(step, "ERROR", {"error": error_message, **(details or {})})
        # Placeholder for GlitchTip integration
        print(f"[ERROR] Step: {step}, Message: {error_message}")
