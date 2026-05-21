import re

with open("game.js", "r") as f:
    js = f.read()

print("=== Snake State Properties ===")
# Find assignments to snake properties like snake.xx = yy
matches = re.findall(r'(\w+)\.(\w{1,3})\s*=', js)
props = {}
for obj, prop in matches:
    if obj in ['s', 'snake', 'sn']:
        props[prop] = props.get(prop, 0) + 1

print("Snake properties (potential):", sorted(props.items(), key=lambda x: -x[1])[:30])

print("\n=== Websocket Opcodes ===")
# Find where the uint8arrays are populated before send
matches = re.findall(r'ba\[0\]\s*=\s*(\d+)', js)
print("Detected WS packet IDs (ba[0]=X):", set(matches))
