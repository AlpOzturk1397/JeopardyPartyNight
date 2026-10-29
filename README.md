# JeopardyPartyNight

Browser-based Jeopardy game for a shared screen and phones/tablets. Players can join as solo players or team members. Each round begins with the host revealing categories one at a time. Solo players can pick a clue; team clue votes count only when all active members of that team agree. Teams share scores and submit one wager and one Final Jeopardy answer per team. Final answers support touch/stylus handwriting, with an optional typed answer. Final Jeopardy has a 60-second writing countdown; when it expires, the host starts a sequential answer reveal, advancing one solo player or team at a time and marking each answer correct, incorrect, or unscored.

## Join page

The host can open the dedicated join page from the editor, or share a room-specific link. The generic join page is the game URL with `?join` appended; it asks for the six-character room code. A room-specific link has `?join=CODE`. Neither join view displays the question editor.

## Internet play

1. Open the hosted game URL on the host computer and select **Start game**.
2. Share the displayed room-specific join link or room code. The host and players need internet access to the page and PeerJS signaling service.
3. Keep the host browser tab open. If a connection drops, phones retry automatically; **Retry connection** is also available.

Internet play uses PeerJS/WebRTC direct connections. Whether browsers can establish a direct connection depends on NAT, VPN, and firewall rules. A network that blocks direct WebRTC requires a TURN relay; the project does not operate a TURN service. PeerJS options, including ICE servers, can be supplied before the application script as `window.JEOPARDY_PEER_OPTIONS` in `index.html`. For example:

```html
<script>
window.JEOPARDY_PEER_OPTIONS = {
  config: {
    iceServers: [{
      urls: "turns:turn.example.net:5349",
      username: "short-lived-user",
      credential: "short-lived-password"
    }]
  }
};
</script>
```

Replace the example with TURN credentials from a service you operate. Do not publish long-lived TURN credentials in a static website: anyone can inspect the page source. Prefer short-lived credentials issued by a protected service. If no TURN service is available, use local-network mode or try another network.

## Local-network play

LAN mode relays game messages through the host computer; it does not depend on PeerJS/WebRTC. It requires Python 3.10 or later and devices that can reach one another on the same Wi-Fi/Ethernet network.

1. Download or clone this repository to the host computer.
2. From the project folder run `python lan_server.py` (Windows may use `py lan_server.py`; macOS/Linux may use `python3 lan_server.py`).
3. Open one of the printed `http://...:8000/` addresses on the host computer. Keep the terminal and browser tab open.
4. Allow inbound TCP port 8000 for Python on a **Private** network in the host firewall. Do not open it to public networks.
5. Start the game and share the room-specific join link or code. Players must use a printed LAN address, not `localhost`, `127.0.0.1`, or the GitHub Pages address.

If port 8000 is occupied, choose another port with `python lan_server.py --port 8080`, then open the printed address. To bind only to a particular interface, use `--host ADDRESS`; the default `0.0.0.0` listens on all interfaces. `--port 0` asks the operating system for an available port and prints the chosen port.

### Connection checks

- On the host, open `http://localhost:8000/api/health`; a working server returns `{"ok":true}`.
- On a phone, open the exact LAN address printed by the server. If the page will not load, check the selected Wi-Fi network, host firewall rule, VPN, and any guest-network/client-isolation setting on the router.
- If the page loads but the room does not connect, confirm the host is still running the game and re-enter the current room code. LAN room state is in memory and ends when the server exits.
- On internet play, confirm both devices can load the hosted page and reach PeerJS signaling. If the room is found but the connection retries indefinitely, try without a VPN or restrictive firewall, use another network, or configure TURN.

The local relay is intended for a trusted home network. It uses plain HTTP and has no authentication; anyone who can reach the server and knows the room code can join. Do not expose it directly to the public internet. The browser app runs on current desktop and mobile browsers; the local server is Python-based and runs on Windows, macOS, and Linux.
