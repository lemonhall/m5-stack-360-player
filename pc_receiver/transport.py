from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Iterator


def iter_simulated_notifications(raw_packets: Iterable[str | bytes]) -> Iterator[str | bytes]:
    yield from raw_packets


async def iter_ble_notifications(
    address: str,
    characteristic_uuid: str,
) -> AsyncIterator[bytes]:
    from asyncio import Queue

    from bleak import BleakClient

    queue: Queue[bytes] = Queue()

    def on_notify(_sender: int, data: bytearray) -> None:
        queue.put_nowait(bytes(data))

    async with BleakClient(address) as client:
        await client.start_notify(characteristic_uuid, on_notify)
        try:
            while True:
                yield await queue.get()
        finally:
            await client.stop_notify(characteristic_uuid)
