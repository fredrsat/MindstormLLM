"""Main control loop: sense-think-act orchestration via Pybricks BLE."""
from __future__ import annotations
import asyncio
import json
import logging
from pathlib import Path
from pybricksdev.ble import find_device
from pybricksdev.connections.pybricks import PybricksHubBLE
from mindstorm.brain.client import Brain, create_brain
from mindstorm.brain.context import Context
from mindstorm.config import load_robot_config, get_reversed_ports, get_driving_pairs
from mindstorm.brain.reasoning import reason
from mindstorm.hub.commands import MotorPairCommand
from mindstorm.hub.state import HubState
from mindstorm.profiles.base import BaseProfile

log = logging.getLogger(__name__)

AGENT_SCRIPT = Path(__file__).parent.parent.parent / "hub_scripts" / "agent.py"


class RobotController:
    """Orchestrates the sense-think-act loop."""

    # Distance thresholds (mm)
    STOP_DISTANCE = 150      # Emergency stop
    SLOW_DISTANCE = 300      # Slow down and prepare to turn
    TURN_DISTANCE = 200      # Stop and turn away

    def __init__(self, profile: BaseProfile, api_key: str | None = None):
        self.profile = profile
        config = load_robot_config()
        self.brain = create_brain(config, api_key=api_key)
        self.context = Context(max_pairs=15)
        self.state = HubState()
        self._running = False
        self._hub: PybricksHubBLE | None = None
        self._cmd_lock = asyncio.Lock()
        self._reversed = get_reversed_ports(config)
        self._pairs = get_driving_pairs(config)
        self._obstacle_detected = False
        self._avoiding = False  # True while executing avoidance maneuver

    async def run(self, hub_name: str | None = None) -> None:
        print(f"\n--- MindstormLLM: {self.profile.name} ---")
        print(f"    {self.profile.description}\n")

        # Find hub
        print("Searching for Pybricks hub...")
        device = await find_device(hub_name or "Pybricks Hub")
        print(f"  Found: {device.name} ({device.address})")

        # Connect
        hub = PybricksHubBLE(device)
        await hub.connect()
        self._hub = hub
        print("  Connected!")

        # Upload and run agent
        print("Uploading agent...")
        # wait=False returns after program starts, line_handler=True enables read_line()
        await hub.run(str(AGENT_SCRIPT), wait=False, print_output=False, line_handler=True)

        # Wait for AGENT_READY
        print("Waiting for AGENT_READY...")
        ready = False
        try:
            for _ in range(30):  # Max 30 lines or ~30 seconds
                text = await asyncio.wait_for(hub.read_line(), timeout=10)
                text = text.strip() if text else ""
                if text:
                    print(f"  Hub: {text}")
                if "AGENT_READY" in text:
                    ready = True
                    break
        except (TimeoutError, asyncio.TimeoutError):
            print("  Timeout waiting for agent!")

        if not ready:
            print("Agent failed to start!")
            await hub.disconnect()
            return

        print(f"\nAgent running! Starting control loop...")
        print(f"Profile: {self.profile.name}")
        print(f"Ports: {self.profile.get_port_config()}")
        print("\nPress Ctrl+C to stop.\n")

        self._running = True

        try:
            await asyncio.gather(
                self._sensor_loop(),
                self._brain_loop(),
                self._distance_safety_loop(),
                self._safety_loop(),
            )
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            self._running = False
            try:
                await hub.write_line(json.dumps({"c": "stop"}))
                await asyncio.sleep(0.2)
                await hub.stop_user_program()
                await asyncio.sleep(0.3)
            except Exception:
                pass
            await hub.disconnect()
            print("\nStopped. Bye!")

    async def _send_cmd(self, cmd: dict) -> dict | None:
        """Send JSON command to hub agent, read JSON response."""
        async with self._cmd_lock:
            line = json.dumps(cmd, separators=(",", ":"))
            try:
                await self._hub.write_line(line)
            except Exception as e:
                log.debug("Write error: %s", e)
                return None

            try:
                resp_text = await asyncio.wait_for(self._hub.read_line(), timeout=3.0)
                if resp_text:
                    return json.loads(resp_text.strip())
            except (TimeoutError, asyncio.TimeoutError):
                log.debug("Read timeout for cmd: %s", cmd.get("c"))
            except (json.JSONDecodeError, Exception) as e:
                log.debug("Response parse error: %s", e)
            return None

    async def _sensor_loop(self) -> None:
        interval = self.profile.sensor_poll_ms / 1000.0
        while self._running:
            resp = await self._send_cmd({"c": "s"})
            if resp and resp.get("ok") and resp.get("d"):
                self.state.update_from_pybricks(resp["d"])
            await asyncio.sleep(interval)

    async def _brain_loop(self) -> None:
        interval = self.profile.llm_call_ms / 1000.0
        await asyncio.sleep(1.5)  # Let sensors populate

        while self._running:
            commands = await reason(
                state=self.state,
                system_prompt=self.profile.system_prompt,
                ports_config=self.profile.get_port_config(),
                brain=self.brain,
                context=self.context,
            )

            # If avoiding obstacle, safety loop controls motors — only send non-motor commands from LLM
            if self._obstacle_detected or self._avoiding:
                commands = self.profile.validate_commands(commands)
                for cmd in commands:
                    d = cmd.to_dict()
                    # Skip motor commands — safety loop handles those
                    if d.get("c") in ("mp", "ms", "md"):
                        continue
                    await self._send_cmd(d)
                print("  (Obstacle: safety override active, LLM motors ignored)")
            else:
                # Normal mode: LLM controls everything
                # If LLM returns only speed=0 commands, use defaults
                all_zero = commands and all(
                    isinstance(c, MotorPairCommand) and c.speed_left == 0 and c.speed_right == 0
                    for c in commands if isinstance(c, MotorPairCommand)
                )
                if not commands or all_zero:
                    commands = self.profile.get_default_commands()

                commands = self.profile.validate_commands(commands)

                for cmd in commands:
                    d = cmd.to_dict()
                    self._apply_reversal(d)
                    await self._send_cmd(d)

            await asyncio.sleep(interval)

    async def _distance_safety_loop(self) -> None:
        """Hardware-level obstacle avoidance with multi-phase maneuver."""
        while self._running:
            min_dist = self._get_min_distance()

            if min_dist >= 0 and min_dist < self.SLOW_DISTANCE:
                if not self._obstacle_detected:
                    print(f"  !! OBSTACLE: {min_dist}mm - starting avoidance")
                self._obstacle_detected = True
                self._avoiding = True
                await self._avoidance_maneuver()
            else:
                if self._obstacle_detected:
                    print(f"  >> Clear! Distance: {min_dist}mm")
                self._obstacle_detected = False
                self._avoiding = False

            await asyncio.sleep(0.1)

    async def _avoidance_maneuver(self) -> None:
        """Execute full avoidance: reverse, then spin until clear."""
        # Phase 1: Reverse away from obstacle
        print("  << Phase 1: Reversing...")
        await self._send_cmd({"c": "di", "i": "FALSE"})
        await self._send_cmd({"c": "sn", "f": 800, "d": 100})
        for _ in range(8):  # ~0.8s reverse
            if not self._running:
                return
            for left, right in self._pairs:
                d = MotorPairCommand(left, right, -180, -180).to_dict()
                self._apply_reversal(d)
                await self._send_cmd(d)
            await asyncio.sleep(0.1)

        # Phase 2: Spin in place until path is clear
        print("  << Phase 2: Spinning...")
        spin_ticks = 0
        max_spin_ticks = 25  # ~2.5s max spin to avoid getting stuck
        while self._running and spin_ticks < max_spin_ticks:
            for left, right in self._pairs:
                d = MotorPairCommand(left, right, -180, 180).to_dict()
                self._apply_reversal(d)
                await self._send_cmd(d)
            await asyncio.sleep(0.1)
            spin_ticks += 1

            # Check if path is now clear
            min_dist = self._get_min_distance()
            if min_dist < 0 or min_dist > self.SLOW_DISTANCE:
                break

        # Phase 3: Brief forward burst at reduced speed to confirm clear
        print(f"  >> Avoidance done (spin: {spin_ticks} ticks)")
        await self._send_cmd({"c": "di", "i": "HAPPY"})
        self._obstacle_detected = False
        self._avoiding = False

    def _get_min_distance(self) -> int:
        """Get minimum distance reading across all distance sensors."""
        min_d = -1
        for reading in self.state.distance_sensors.values():
            d = reading.distance_mm
            if d >= 0:
                if min_d < 0 or d < min_d:
                    min_d = d
        return min_d

    def _apply_reversal(self, d: dict) -> None:
        """Apply motor reversal to a command dict."""
        if self._reversed:
            if d.get("c") == "mp":
                if d.get("l") in self._reversed:
                    d["sl"] = -d["sl"]
                if d.get("r") in self._reversed:
                    d["sr"] = -d["sr"]
            elif d.get("c") in ("ms", "md") and d.get("p") in self._reversed:
                d["v"] = -d["v"]

    async def _safety_loop(self) -> None:
        while self._running:
            if self.state.battery_pct < 10:
                log.warning("Low battery! Stopping.")
                await self._send_cmd({"c": "stop"})
                self._running = False
                return

            if self.state.imu.gesture == "shake":
                log.warning("Shake - emergency stop!")
                await self._send_cmd({"c": "stop"})

            await asyncio.sleep(0.05)

    def stop(self) -> None:
        self._running = False
