from enum import Enum

class FlowState(Enum):
    INIT = "initiated"
    START = "start"
    # Add other states as needed

    def to_log_message(self, detail="", **kwargs):
        """Convert an enum state to a log message dictionary."""
        base_message = {"flow": self.value, "status": self.name.lower()}
        if detail:
            base_message["detail"] = detail.format(**kwargs)
        return base_message
