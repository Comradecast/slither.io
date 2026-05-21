import re
import sys

def analyze():
    with open("game.js", "r") as f:
        js = f.read()

    # Look for snake arrays and object definitions
    print("=== State Analysis ===")

    # snakes array is usually global, often "snakes = []"
    matches = re.findall(r'(\w+)\s*=\s*\[\];[^;]*\w+\.push\(', js)
    print("Potential Global Arrays (Snakes/Food):", set(matches))

    # Look for websocket send actions
    print("\n=== Action/WebSocket Opcode Analysis ===")
    send_matches = re.findall(r'ws\.send\((.*?)\)', js)
    for m in set(send_matches):
        print(f"ws.send({m})")

    # Look for Uint8Array usage which signifies protocol framing
    uint_matches = re.findall(r'new Uint8Array\((.*?)\)', js)
    print("\nUint8Array allocations:", set(uint_matches))

analyze()
