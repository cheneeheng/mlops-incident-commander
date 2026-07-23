"""Synthetic traffic generator. Stub at SKELETON; real CIFAR-10 sampling + injection transforms
land in ITER_01. Note: the traffic generator runs against the serving app, so it is started by the
serving process (serving/app/main.py), not the control plane."""

import asyncio


async def run_traffic_generator() -> None:
    # stub — real implementation in ITER_01
    await asyncio.sleep(0)
