# JeopardyPartyNight

Browser-based Jeopardy game for a shared screen and phone buzzers. Shout out to Brian Yu's Jeopardy game: https://jeopardy.brianyu.me/

## Joining a game

1. Open the game on the host screen and select **Start game**.
2. Share the displayed room code or join link. Players can open the link, or open the game page and enter the six-character code.
3. Keep the host page open for the duration of the game. If a phone loses its connection, it retries automatically; **Retry connection** is available on the phone.

The game is a static GitHub Pages site and uses PeerJS for signaling and browser-to-browser WebRTC connections. Some restrictive Wi-Fi, VPN, and mobile networks block peer-to-peer connections. Those networks require a TURN relay, which needs a separately configured service; GitHub Pages cannot provide that relay itself. Try switching networks (for example, Wi-Fi to cellular) if a phone cannot connect.
