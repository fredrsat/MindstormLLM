"""Discover Pybricks hubs via BLE."""
import asyncio
from bleak import BleakScanner, BLEDevice, AdvertisementData

PYBRICKS_SERVICE_UUID = "c5f50001-8280-46da-89f4-6d8051e4aeef"


async def find_hubs(timeout: float = 15.0) -> list[BLEDevice]:
    """Scan for Pybricks hubs. Returns as soon as one is found."""
    print(f"Scanning for Pybricks hubs (max {timeout}s)...")
    found: list[BLEDevice] = []
    event = asyncio.Event()

    def callback(device: BLEDevice, adv: AdvertisementData):
        name = device.name or ""
        if "pybricks" in name.lower():
            if device not in found:
                found.append(device)
                print(f"  Found: {name} ({device.address})")
                event.set()

    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        pass
    await scanner.stop()
    return found


async def find_hub(name: str | None = None, timeout: float = 15.0) -> BLEDevice | None:
    """Find a single Pybricks hub."""
    hubs = await find_hubs(timeout)
    if not hubs:
        return None
    if name:
        for h in hubs:
            if h.name and name.lower() in h.name.lower():
                return h
        return None
    return hubs[0]
