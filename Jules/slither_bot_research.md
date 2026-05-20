# Slither.io Bot Research Brief

## Findings: Game Mechanics
Slither.io is a massively multiplayer online game where players control a snake, consume colorful orbs to grow longer, and attempt to survive by cutting off other players. 
* **Movement:** The snake moves continuously forward toward the mouse cursor.
* **Growth:** Consuming orbs increases length and score. Larger orbs provide more mass. When a snake dies, it drops orbs proportional to its size, though a fraction is lost.
* **Collision:** If a snake's head touches another snake's body, the snake dies. Hitting your own body does not cause death. Hitting the map boundary causes death.
* **Boost:** Pressing the mouse button or spacebar uses boost. Boosting consumes mass (shrinking the snake slightly) but increases speed, allowing players to outmaneuver opponents.
* **"Good Play":** Advanced strategies involve "coiling" (encircling smaller snakes to trap them), boosting to cut off opponents, and safely scavenging mass from recently deceased large snakes without over-committing and getting cut off.

## Technical Notes
The browser client communicates with the server primarily via WebSockets.
* **Protocol:** The network protocol uses a custom binary format over WebSockets for performance. Information such as movement updates, new food entities, snake deaths, and leaderboard updates are streamed continuously.
* **Client-Side Rendering:** The game uses HTML5 Canvas to render the game state.
* **Obfuscation:** The client-side JavaScript is minified and obfuscated. Variable and function names change between versions.
* **Security Constraints:** Any direct interaction with the WebSocket or injected JS must be mindful of potential anti-cheat mechanisms, rate limits, and server-side validation of movement vectors (to prevent teleportation or impossible turns).

## Existing Solutions
Several open-source projects have attempted to tackle Slither.io bots with varying degrees of success:
* **Protocol Reverse Engineering:** Projects like `ClitherProject/Slither.io-Protocol` (Ruby/JS) have successfully documented the binary protocol, mapping out opcodes for handshakes, movement, and game events.
* **Deep Learning via Browser Automation:** Projects like `ryanrudes/slitherio` and `matsokolowski/slitherDLBOT` utilize Python + Selenium to control a browser instance. They capture screenshots, process them (sometimes using CNNs/Reinforcement Learning), and send mouse movement commands.
* **In-browser AI:** Projects like `pirobtumen/Slither.AI` inject JavaScript directly into the page to read the game state from the obfuscated variables and manipulate the snake's target coordinates.

## Botting Approaches Evaluated

### 1. Browser Automation / Visual Bot (e.g., Python + Playwright/Selenium + OpenCV/RL)
* **Description:** Run a real browser, capture screenshots, analyze frames visually, and simulate mouse movements.
* **Pros:** Completely decoupled from the game's code/protocol. Immune to obfuscation changes or protocol updates. Safest from an anti-cheat perspective as it acts exactly like a human player.
* **Cons:** Extremely high overhead. Processing frames via CV or neural networks in real-time is computationally expensive and introduces latency.
* **Realistic?** Yes, but challenging to make competitive due to latency and the difficulty of extracting precise state from raw pixels.

### 2. In-Page JavaScript Inspection (e.g., Tampermonkey script)
* **Description:** Inject custom JavaScript into the browser to read the game's internal memory state (snake arrays, food arrays) and override the target mouse coordinates.
* **Pros:** Perfect knowledge of the local game state (no CV required). Low latency. Relatively easy to prototype using existing browser developer tools.
* **Cons:** Highly brittle. Every time the game updates its obfuscated code, the script must be updated to find the new variable names.
* **Realistic?** Yes, this is a very common approach for browser games, but requires ongoing maintenance.

### 3. Headless / Protocol-Level Client
* **Description:** Completely bypass the browser and communicate directly with the Slither.io servers using WebSockets by implementing the binary protocol.
* **Pros:** Extreme performance. Minimal resource usage. Allows running hundreds of bots simultaneously.
* **Cons:** Massive upfront effort to reverse engineer and maintain the protocol. High risk of detection if the handshake or movement signatures fail server-side validation.
* **Realistic?** Possible (as proven by ClitherProject), but highly complex and prone to breaking with minor server updates. Also edges close to the "avoid" constraints regarding abuse.

### 4. Hybrid Approach (Recommended)
* **Description:** Use a browser automation tool (like Playwright in Python) to load the game, handle the complex handshake/initialization, and then either intercept the WebSocket traffic or inject a lightweight JS bridge to extract the parsed game state.
* **Pros:** Avoids reverse-engineering the handshake/login. Provides clean state data without the overhead of Computer Vision. Allows using Python for the complex logic/ML without maintaining a raw WebSocket client.
* **Cons:** Still somewhat brittle to major game updates.
* **Realistic?** Yes, this balances development speed with performance.

## Recommended Approach & Next Steps

**Recommended Architecture:** The **Hybrid Approach** using Python + Playwright with an injected JavaScript bridge. 
This allows us to leverage Python for analysis, tooling, and future bot logic, while relying on the browser to handle the complex rendering and networking. By injecting a JS bridge, we can extract the internal game state (food locations, enemy snakes) and expose it to Python, avoiding the high latency of visual processing.

**Is it technically feasible?** Yes. Existing projects have proven that extracting state via JS and controlling the snake via automation is viable.

**First Small Prototype:**
1. Setup a Python Playwright script to launch `slither.io` in a headless (or visible for debugging) browser.
2. Inject a simple JavaScript snippet that attempts to locate the player's current X/Y coordinates and score from the global window variables.
3. Successfully log this data back to the Python console continuously as the player (human) controls the snake.

**What to Avoid:**
* Do not attempt to reverse engineer the raw WebSocket protocol at this stage. It is time-consuming and fragile.
* Avoid spamming the server with connections. Stick to a single browser instance for research.
* Avoid full pixel-based Reinforcement Learning for now, as the latency and setup complexity will hinder initial progress.
