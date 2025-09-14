#!/usr/bin/env python3
import asyncio
import random
import datetime
from aiohttp import web

# In-memory telemetry state
switches = ["switch1", "switch2", "switch3","switch4","switch5"]
metrics = ["bandwidth", "latency", "errors"]
telemetry = {}

# Initialize with random values
def init_telemetry():
    global telemetry
    telemetry = {}
    for sw in switches:
        telemetry[sw] = {
            "bandwidth": random.uniform(10, 100),
            "latency": random.uniform(0.1, 1),
            "errors": random.randint(0, 5)
        }

# Periodically update telemetry
async def update_telemetry():
    while True:
        for sw in switches:
            telemetry[sw]["bandwidth"] = random.uniform(10, 100)
            telemetry[sw]["latency"] = random.uniform(0.1, 1.0)
            telemetry[sw]["errors"] = random.randint(0, 5)
        await asyncio.sleep(1)

# REST endpoint: return CSV
async def get_counters(request):
    lines = []
    header = ["switch_id"] + metrics + ["timestamp"]
    lines.append(",".join(header))
    now = datetime.datetime.now(datetime.UTC).isoformat()
    for sw, vals in telemetry.items():
        row = [sw] + [str(vals[m]) for m in metrics] + [now]
        lines.append(",".join(row))
    csv_text = "\n".join(lines)
    return web.Response(text=csv_text, content_type="text/csv")

# Main app setup
async def main():
    init_telemetry()
    app = web.Application()
    app.router.add_get("/counters", get_counters)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 9001)
    await site.start()

    # Start background telemetry updater
    asyncio.create_task(update_telemetry())

    print("[INFO] Telemetry generator running at http://127.0.0.1:9001/counters")
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())