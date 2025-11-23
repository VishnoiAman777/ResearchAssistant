"""Utility helpers for agent output rendering."""

import json
from typing import Iterable

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def format_message_content(message) -> str:
	"""Convert message content to displayable string."""
	parts = []
	tool_calls_processed = False

	if isinstance(message.content, str):
		parts.append(message.content)
	elif isinstance(message.content, list):
		for item in message.content:
			if item.get("type") == "text":
				parts.append(item["text"])
			elif item.get("type") == "tool_use":
				parts.append(f"\n🔧 Tool Call: {item['name']}")
				parts.append(f"   Args: {json.dumps(item['input'], indent=2)}")
				parts.append(f"   ID: {item.get('id', 'N/A')}")
				tool_calls_processed = True
	else:
		parts.append(str(message.content))

	if not tool_calls_processed and hasattr(message, "tool_calls") and message.tool_calls:
		for tool_call in message.tool_calls:
			parts.append(f"\n🔧 Tool Call: {tool_call['name']}")
			parts.append(f"   Args: {json.dumps(tool_call['args'], indent=2)}")
			parts.append(f"   ID: {tool_call['id']}")

	return "\n".join(parts)


def format_messages(messages: Iterable):
	"""Format and display a list of messages with Rich formatting."""
	for message in messages:
		msg_type = message.__class__.__name__.replace("Message", "")
		content = format_message_content(message)

		if msg_type == "Human":
			console.print(Panel(content, title="🧑 Human", border_style="blue"))
		elif msg_type == "Ai":
			console.print(Panel(content, title="🤖 Assistant", border_style="green"))
		elif msg_type == "Tool":
			console.print(Panel(content, title="🔧 Tool Output", border_style="yellow"))
		else:
			console.print(Panel(content, title=f"📝 {msg_type}", border_style="white"))


def format_message(messages: Iterable):
	"""Alias for format_messages for backward compatibility."""
	return format_messages(messages)


def show_prompt(prompt_text: str, title: str = "Prompt", border_style: str = "blue"):
	"""Display a prompt with rich formatting and XML tag highlighting."""
	formatted_text = Text(prompt_text)
	formatted_text.highlight_regex(r"<[^>]+>", style="bold blue")
	formatted_text.highlight_regex(r"##[^#\n]+", style="bold magenta")
	formatted_text.highlight_regex(r"###[^#\n]+", style="bold cyan")

	console.print(
		Panel(
			formatted_text,
			title=f"[bold green]{title}[/bold green]",
			border_style=border_style,
			padding=(1, 2),
		)
	)
