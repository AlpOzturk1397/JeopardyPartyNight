# JeopardyPartyNight

Browser-based Jeopardy game for a shared screen and phone buzzers. Shout out to Brian Yu's Jeopardy game: https://jeopardy.brianyu.me/

## Joining a game on GitHub Pages

1. Open the game on the host screen and select **Start game**.
2. Share the displayed room code or join link. Players can open the link, or open the game page and enter the six-character code.
3. Keep the host page open for the duration of the game. If a phone loses its connection, it retries automatically; **Retry connection** is available on the phone.

GitHub Pages uses PeerJS to connect browsers directly. Some networks block direct WebRTC connections, even when both devices are on the same Wi-Fi. Those networks require a TURN relay, which needs a separately configured service.

## Joining over your local network

The local mode relays game messages through the host laptop instead of using PeerJS/WebRTC. It needs Python 3, and the laptop and phones must be on the same Wi-Fi/LAN.

1. Download or clone this repository onto the laptop.
2. Open a terminal in the downloaded folder and run `python lan_server.py` (on Windows, `py lan_server.py` also works).
3. If Windows Firewall asks, allow Python on **Private networks**.
4. Open one of the `http://...:8000/` addresses printed by the server on the host laptop. Keep the terminal and browser page open.
5. Start the game and share the displayed link or six-character room code. Phones must use the printed laptop LAN address, not `localhost` or the GitHub Pages URL.

Stop the server with Ctrl+C. This local relay is intended for a trusted home network; anyone who can reach the laptop and knows the room code can join.
