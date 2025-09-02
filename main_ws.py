import asyncio
import json
import sys
import websockets

WS_URL = "ws://127.0.0.1:5000/api/v1/tasks/{task_id}/ws"


async def listen_task(task_id: str):
    url = WS_URL.format(task_id=task_id)
    print(f"Connecting to {url}")

    try:
        async with websockets.connect(url) as websocket:
            async for message in websocket:
                try:
                    data = json.loads(message)
                except Exception:
                    print("Non-JSON message:", message)
                    continue

                print("Task update:", json.dumps(data, indent=2))

                if data.get("status") in ("SUCCESS", "FAILURE", "ERROR"):
                    print("Task finished.")
                    break

    except Exception as e:
        print("WebSocket error:", e)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main_ws.py <task_id>")
        sys.exit(1)

    task_id = sys.argv[1]
    asyncio.run(listen_task(task_id))
