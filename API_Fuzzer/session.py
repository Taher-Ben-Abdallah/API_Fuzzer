import json
import yaml
from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum

"""
{   "session_name":"A new session",
    "config": {
        "request": {
            "headers": {"User-Agent": "Mozilla/5.0 (Mac)"}
        },
        "fuzz_engine": {
            "workers": 4,
        },
    },
    "operations": [
        {"type": "fuzz", "details": {"request":"GET http:// ...","used_wordlists":{}, "status": "paused"}, "timestamp": "..."},
        {"type": "discovery", "details": {"endpoint": "/api/login", "status": "failed"}, "timestamp": "..."},
        {"type": "wordlist_merge", "details": {"files": ["file1.txt", "file2.txt"], "status": "success"}, "timestamp": "..."}
    ],
    "session_lifecycle": [{"start_time": "2023-10-31T10:00:00", "end_time": "2023-10-31T11:00:00"},],
}
"""

session_template = {}


class OperationType(Enum):
    FUZZ = "fuzz"
    API_DISCOVERY = "api_discovery"
    WORDLIST_MERGE = "wordlist_merge"
    PAYLOAD_GENERATION = "payload_generation"


class Session(dict):
    def __init__(self, session_name="Untitled_session", conf: Optional[Dict[str, Any]] = None,
                 loaded_session: Optional[Dict[str, Any]] = None):
        """
        Initialize a session with a new or loaded configuration.

        Args:
            conf (Optional[Dict[str, Any]]): The initial configuration for the session.
            loaded_session (Optional[Dict[str, Any]]): A loaded session dictionary to restore state.
        """

        super().__init__()

        if conf is None:
            conf = {}

        if loaded_session:
            # Load session data
            self.update(loaded_session)
            self.session_lifecycle = loaded_session.get("session_lifecycle", [])
            self['config'].update(conf)
            # Check if the last entry in session_lifecycle is active
            self.active = not self.session_lifecycle[-1].get("end_time") if self.session_lifecycle else True
        else:
            # Initialize new session
            self["session_name"] = session_name
            self["config"] = conf
            self["operations"] = []
            self.session_lifecycle = []
            self.start_session()

    def start_session(self):
        """Start a new session cycle and mark it as active."""
        self.session_lifecycle.append({"start_time": datetime.now().isoformat(), "end_time": None})
        self.active = True

    def update_operation(self, operation_type: OperationType, details: Dict[str, Any]):
        """
        Add an operation to the session, with type validation.

        Args:
            operation_type (OperationType): The type of operation.
            details (Dict[str, Any]): Details of the operation, such as parameters used.
        """
        if not self.active:
            raise RuntimeError("Cannot add operation to a terminated session.")

        operation_entry = {
            "type": operation_type.value,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self["operations"].append(operation_entry)

    def update_config(self, new_conf: Dict[str, Any]):
        """
        Replace the session configuration with a new configuration dictionary.

        Args:
            new_conf (Dict[str, Any]): The new configuration to replace the current config.
        """
        self["config"] = new_conf

    def end_session(self):
        """Terminate the session, marking the latest session lifecycle as inactive."""

        if self.session_lifecycle and not self.session_lifecycle[-1]["end_time"]:
            self.session_lifecycle[-1]["end_time"] = datetime.now().isoformat()
            self.active = False

    def save(self):
        self.end_session()
        self["session_lifecycle"] = self.session_lifecycle

    '''def save(self, filename: str, file_format: Optional[str] = "json"):
        """
        Save the session to a file in JSON or YAML format.

        Args:
            filename (str): The name of the file to save to.
            file_format (Optional[str]): The file format, either "json" or "yaml".
        """
        self["session_lifecycle"] = self.session_lifecycle  # Add session lifecycle to saved data
        with open(filename, 'w') as file:
            if file_format == "yaml":
                yaml.dump(dict(self), file)
            else:
                json.dump(self, file, indent=4)
    '''

    def __repr__(self):
        return f"<Session active={self.active} operations={len(self['operations'])}>"



if __name__ == '__main__':
    # Example usage:
    # Initial configuration
    from config import Config

    config = Config()
    # Initialize a new session
    session1 = Session(session_name="Session1111",conf=config)
    session1.start_session()
    print("S1-Initial Session: ", dict(session1))
    # Update session with different operations
    session1.update_operation(OperationType.FUZZ, {"request": "GET http:// ...", "used_wordlists": {}, "status": "paused"})
    session1.update_operation(OperationType.API_DISCOVERY, {"endpoint": "/api/login", "status": "failed"})
    print("S1-After : ", dict(session1))

    session2 = Session(session_name="Session2222", loaded_session=dict(session1))
    print("S2-Initial Session: ", dict(session2))
    # Replace the session configuration
    new_config = {
        "request": {
            "headers": {"Host": "localhost", "User-Agent": "Mozilla/5.0 (Windows)"}
        },
        "fuzz_engine": {
            "workers": 6,
        },
    }
    session2.update_config(new_config)

    # Terminate and save
    session1.end_session()
    session2.save()

    print("S1-FINAL: ", dict(session1))
    print("S2-FINAL: ", dict(session2))
