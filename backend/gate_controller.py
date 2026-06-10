"""
Barrier gate abstraction layer.
Supports: network relay (HTTP/TCP), GPIO, and simulated (dev/test).
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import requests
from config import Config

logger = logging.getLogger(__name__)


@dataclass
class GateStatus:
    gate_id: str
    is_open: bool
    last_action: Optional[str] = None
    updated_at: Optional[str] = None


class GateController(ABC):
    """Abstract interface for barrier gate control."""

    @abstractmethod
    def open(self, gate_id: str) -> bool:
        """Open the barrier gate. Returns True on success."""

    @abstractmethod
    def close(self, gate_id: str) -> bool:
        """Close the barrier gate. Returns True on success."""

    @abstractmethod
    def get_status(self, gate_id: str) -> GateStatus:
        """Get current gate status."""


class NetworkRelayController(GateController):
    """
    Controls barrier gates via HTTP network relay module.
    Typical relay module API:
      GET /relay/0?state=1  →  activate relay 0 (open gate)
      GET /relay/0?state=0  →  deactivate relay 0 (close gate)
    """

    def __init__(self, host: str = None, port: int = None):
        self.host = host or Config.GATE_RELAY_HOST
        self.port = port or Config.GATE_RELAY_PORT
        self._states: dict[str, bool] = {}
        logger.info("NetworkRelayController initialized: %s:%s", self.host, self.port)

    def _send(self, channel: int, state: int) -> bool:
        try:
            url = f"http://{self.host}:{self.port}/relay/{channel}"
            resp = requests.get(url, params={"state": state}, timeout=5)
            return resp.status_code == 200
        except Exception as e:
            logger.error("Relay command failed: channel=%d state=%d error=%s", channel, state, e)
            return False

    def open(self, gate_id: str) -> bool:
        channel = self._gate_to_channel(gate_id)
        ok = self._send(channel, 1)
        if ok:
            self._states[gate_id] = True
            logger.info("Gate opened: %s", gate_id)
        return ok

    def close(self, gate_id: str) -> bool:
        channel = self._gate_to_channel(gate_id)
        ok = self._send(channel, 0)
        if ok:
            self._states[gate_id] = False
            logger.info("Gate closed: %s", gate_id)
        return ok

    def get_status(self, gate_id: str) -> GateStatus:
        is_open = self._states.get(gate_id, False)
        return GateStatus(
            gate_id=gate_id,
            is_open=is_open,
            updated_at=datetime.now().isoformat(),
        )

    @staticmethod
    def _gate_to_channel(gate_id: str) -> int:
        """Map gate logical ID to relay channel number."""
        mapping = {"entry_gate": 0, "exit_gate": 1, "main_gate_entry": 0, "main_gate_exit": 1}
        return mapping.get(gate_id, 0)


class GPIOController(GateController):
    """For Raspberry Pi / embedded boards with GPIO-connected relays."""

    def open(self, gate_id: str) -> bool:
        logger.info("GPIO gate open (simulated): %s", gate_id)
        return True

    def close(self, gate_id: str) -> bool:
        logger.info("GPIO gate close (simulated): %s", gate_id)
        return True

    def get_status(self, gate_id: str) -> GateStatus:
        return GateStatus(gate_id=gate_id, is_open=False)


class SimulatedController(GateController):
    """Prints gate commands instead of executing — for development/testing."""

    def open(self, gate_id: str) -> bool:
        logger.info("[SIMULATED] Gate OPEN: %s at %s", gate_id, datetime.now().isoformat())
        return True

    def close(self, gate_id: str) -> bool:
        logger.info("[SIMULATED] Gate CLOSE: %s at %s", gate_id, datetime.now().isoformat())
        return True

    def get_status(self, gate_id: str) -> GateStatus:
        return GateStatus(gate_id=gate_id, is_open=False, last_action="simulated")


def create_gate_controller(control_type: str = "simulated") -> GateController:
    """Factory: create the appropriate gate controller based on config."""
    types = {
        "network_relay": NetworkRelayController,
        "gpio": GPIOController,
        "simulated": SimulatedController,
    }
    cls = types.get(control_type, SimulatedController)
    return cls()
