"""
Karma Kadabra V2 — Task 5.5: MeshRelay IRC Integration

Connects KK agents to MeshRelay IRC for real-time communication,
marketplace negotiations, and deal execution.

Channels:
  #Agents         — General agent communication
  #kk-ops         — Swarm coordination (system agents only)
  #kk-data-market — Data marketplace (buy/sell offerings)

Agent behaviors:
  - Post "HAVE:" messages when publishing new EM offerings
  - Post "NEED:" messages when looking for specific data
  - Respond to queries about their skills/capabilities
  - Negotiate deals that execute on EM

Usage:
  python agent_irc_client.py --agent kk-juanjumagalp
  python agent_irc_client.py --agent kk-coordinator --channel "#kk-ops"
  python agent_irc_client.py --list-agents
"""

import argparse
import asyncio
import json
import logging
import random
import socket
import ssl
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("kk.irc")

# IRC server config
IRC_SERVER = "irc.meshrelay.xyz"
IRC_PORT = 6667
IRC_SSL_PORT = 6697
DEFAULT_CHANNELS = ["#Agents", "#kk-data-market"]
RECONNECT_DELAY = 30
PING_INTERVAL = 120


class IRCAgent:
    """Single KK agent connected to MeshRelay IRC."""

    def __init__(
        self,
        nick: str,
        channels: list[str],
        workspace_dir: Path | None = None,
        use_ssl: bool = False,
    ):
        self.nick = nick
        self.channels = channels
        self.workspace_dir = workspace_dir
        self.use_ssl = use_ssl
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False
        self._running = True

        # Load agent profile for personality
        self._profile: dict = {}
        self._skills: list[str] = []
        self._load_profile()

    def _load_profile(self) -> None:
        if not self.workspace_dir:
            return
        soul_file = self.workspace_dir / "SOUL.md"
        profile_file = self.workspace_dir / "data" / "profile.json"

        if profile_file.exists():
            data = json.loads(profile_file.read_text(encoding="utf-8"))
            self._profile = data
            self._skills = [s.get("skill", "") for s in data.get("top_skills", [])]

    async def connect(self) -> None:
        """Connect to IRC server."""
        port = IRC_SSL_PORT if self.use_ssl else IRC_PORT

        logger.info(f"  [{self.nick}] Connecting to {IRC_SERVER}:{port}...")

        if self.use_ssl:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            self._reader, self._writer = await asyncio.open_connection(
                IRC_SERVER, port, ssl=ctx,
            )
        else:
            self._reader, self._writer = await asyncio.open_connection(
                IRC_SERVER, port,
            )

        # Register with server
        await self._send(f"NICK {self.nick}")
        await self._send(f"USER {self.nick} 0 * :KK Agent {self.nick}")

        # Wait for welcome (001)
        while True:
            line = await self._recv()
            if not line:
                break
            if " 001 " in line:
                self._connected = True
                logger.info(f"  [{self.nick}] Connected!")
                break
            if "PING" in line:
                await self._handle_ping(line)

        # Join channels
        for channel in self.channels:
            await self._send(f"JOIN {channel}")
            logger.info(f"  [{self.nick}] Joined {channel}")

    async def _send(self, msg: str) -> None:
        if self._writer:
            self._writer.write(f"{msg}\r\n".encode("utf-8"))
            await self._writer.drain()

    async def _recv(self) -> str:
        if self._reader:
            try:
                data = await asyncio.wait_for(self._reader.readline(), timeout=PING_INTERVAL + 30)
                return data.decode("utf-8", errors="replace").strip()
            except asyncio.TimeoutError:
                return ""
        return ""

    async def _handle_ping(self, line: str) -> None:
        token = line.split("PING ")[-1] if "PING " in line else ":server"
        await self._send(f"PONG {token}")

    async def send_message(self, channel: str, message: str) -> None:
        """Send a message to a channel."""
        await self._send(f"PRIVMSG {channel} :{message}")

    async def announce_offering(self, channel: str, title: str, bounty: float) -> None:
        """Announce a new EM offering on IRC."""
        msg = f"HAVE: {title} | ${bounty:.2f} USDC | Browse at execution.market"
        await self.send_message(channel, msg)

    async def post_need(self, channel: str, description: str, budget: float) -> None:
        """Post a need/request on IRC."""
        msg = f"NEED: {description} | Budget: ${budget:.2f} USDC | DM me or check EM"
        await self.send_message(channel, msg)

    async def introduce(self, channel: str) -> None:
        """Introduce agent to the channel."""
        skills_str = ", ".join(self._skills[:3]) if self._skills else "general"
        msg = f"Hey! I'm {self.nick} from KK swarm. Skills: {skills_str}. Browsing tasks on EM."
        await self.send_message(channel, msg)

    async def handle_message(self, sender: str, channel: str, message: str) -> None:
        """Handle an incoming IRC message."""
        msg_lower = message.lower()

        # Respond to direct mentions
        if self.nick.lower() in msg_lower:
            if "skills" in msg_lower or "what can you do" in msg_lower:
                skills_str = ", ".join(self._skills[:5]) if self._skills else "general knowledge"
                await self.send_message(channel, f"{sender}: My skills: {skills_str}")
            elif "help" in msg_lower:
                await self.send_message(
                    channel,
                    f"{sender}: I buy/sell data on execution.market. Ask me about my offerings!",
                )

        # Respond to marketplace queries
        if channel == "#kk-data-market":
            if msg_lower.startswith("need:") and any(s.lower() in msg_lower for s in self._skills):
                await self.send_message(
                    channel,
                    f"{sender}: I might be able to help with that! Check my offerings on EM.",
                )

    async def listen(self) -> None:
        """Main listen loop — process incoming messages."""
        logger.info(f"  [{self.nick}] Listening...")

        while self._running and self._connected:
            line = await self._recv()
            if not line:
                # Possible timeout — send ping
                await self._send(f"PING :keepalive-{int(time.time())}")
                continue

            if line.startswith("PING"):
                await self._handle_ping(line)
                continue

            # Parse PRIVMSG: :nick!user@host PRIVMSG #channel :message
            if "PRIVMSG" in line:
                try:
                    prefix, _, rest = line.partition(" PRIVMSG ")
                    sender = prefix.split("!")[0].lstrip(":")
                    channel, _, message = rest.partition(" :")
                    await self.handle_message(sender, channel, message)
                except Exception:
                    pass

    async def disconnect(self) -> None:
        """Disconnect from IRC."""
        self._running = False
        if self._writer:
            await self._send("QUIT :KK agent signing off")
            self._writer.close()
        logger.info(f"  [{self.nick}] Disconnected")


async def run_agent(
    agent_name: str,
    workspace_dir: Path | None,
    channels: list[str],
    introduce: bool = True,
    duration: int = 0,
) -> None:
    """Run a single IRC agent."""
    agent = IRCAgent(
        nick=agent_name,
        channels=channels,
        workspace_dir=workspace_dir,
    )

    try:
        await agent.connect()

        if introduce:
            await asyncio.sleep(2)
            for ch in channels:
                await agent.introduce(ch)

        if duration > 0:
            # Run for specified duration
            try:
                await asyncio.wait_for(agent.listen(), timeout=duration)
            except asyncio.TimeoutError:
                pass
        else:
            await agent.listen()

    except Exception as e:
        logger.error(f"  [{agent_name}] Error: {e}")
    finally:
        await agent.disconnect()


def list_available_agents(workspaces_dir: Path) -> list[str]:
    """List all available agent workspaces."""
    manifest = workspaces_dir / "_manifest.json"
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return [ws["name"] for ws in data.get("workspaces", [])]
    return [d.name for d in workspaces_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]


async def main():
    parser = argparse.ArgumentParser(description="KK Agent IRC Client")
    parser.add_argument("--agent", type=str, help="Agent name (e.g., kk-juanjumagalp)")
    parser.add_argument("--channel", type=str, action="append", help="IRC channel to join")
    parser.add_argument("--workspaces", type=str, default=None)
    parser.add_argument("--duration", type=int, default=0, help="Run duration in seconds (0=forever)")
    parser.add_argument("--no-intro", action="store_true", help="Skip channel introduction")
    parser.add_argument("--list-agents", action="store_true")
    args = parser.parse_args()

    base = Path(__file__).parent.parent
    workspaces_dir = Path(args.workspaces) if args.workspaces else base / "data" / "workspaces"

    if args.list_agents:
        agents = list_available_agents(workspaces_dir)
        print(f"\nAvailable agents ({len(agents)}):")
        for a in agents:
            print(f"  - {a}")
        return

    if not args.agent:
        print("ERROR: --agent required. Use --list-agents to see available agents.")
        return

    channels = args.channel or DEFAULT_CHANNELS
    workspace_dir = workspaces_dir / args.agent
    if not workspace_dir.exists():
        workspace_dir = workspaces_dir / f"kk-{args.agent}"

    print(f"\n{'=' * 60}")
    print(f"  KK IRC Agent: {args.agent}")
    print(f"  Server: {IRC_SERVER}")
    print(f"  Channels: {', '.join(channels)}")
    print(f"{'=' * 60}\n")

    await run_agent(
        agent_name=args.agent,
        workspace_dir=workspace_dir if workspace_dir.exists() else None,
        channels=channels,
        introduce=not args.no_intro,
        duration=args.duration,
    )


if __name__ == "__main__":
    asyncio.run(main())
