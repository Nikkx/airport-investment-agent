from collections.abc import Callable
from pathlib import Path

from google import genai
from google.genai import errors
from google.genai import types

from tools import (
    assess_unmet_demand as fetch_unmet_demand,
    calculate_expansion_score as fetch_expansion_score,
    calculate_long_haul_percentage as fetch_long_haul_percentage,
)


def load_agent_instructions() -> str:
    instructions_path = Path(__file__).with_name("agent_instructions.txt")
    try:
        with instructions_path.open("r", encoding="utf-8") as file:
            return file.read()
    except OSError as exc:
        raise RuntimeError(
            f"Unable to load agent instructions from {instructions_path}."
        ) from exc


def create_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def build_expansion_tool(
    aviationstack_key: str,
) -> Callable[[str], dict[str, object]]:
    def calculate_expansion_score(airport_code: str) -> dict:
        """Fetch live airport data and calculate its expansion score."""
        return fetch_expansion_score(airport_code, aviationstack_key)

    return calculate_expansion_score


def build_long_haul_tool(
    aviationstack_key: str,
) -> Callable[[str], dict[str, object]]:
    def calculate_long_haul_percentage(airport_code: str) -> dict:
        """Calculate an airport's long-haul flight percentage from live data."""
        return fetch_long_haul_percentage(airport_code, aviationstack_key)

    return calculate_long_haul_percentage


def build_unmet_demand_tool(
    aviationstack_key: str,
) -> Callable[[str], dict[str, object]]:
    def assess_unmet_demand(airport_code: str) -> dict:
        """Assess operational indicators related to unmet demand."""
        return fetch_unmet_demand(airport_code, aviationstack_key)

    return assess_unmet_demand


def create_chat_session(client: genai.Client, aviationstack_key: str):
    """Create a Gemini chat session with the configured aviation tools."""
    instructions = load_agent_instructions()
    expansion_tool = build_expansion_tool(aviationstack_key)
    long_haul_tool = build_long_haul_tool(aviationstack_key)
    unmet_demand_tool = build_unmet_demand_tool(aviationstack_key)

    return client.chats.create(
        model="gemini-3.5-flash-lite",
        config=types.GenerateContentConfig(
            tools=[expansion_tool, long_haul_tool, unmet_demand_tool],
            system_instruction=instructions,
        ),
    )


def send_prompt(chat_session, prompt: str):
    """Send a prompt and translate common Gemini service errors."""
    try:
        return chat_session.send_message(prompt)
    except errors.ClientError as e:
        if e.code == 429:
            raise RuntimeError(
                "Gemini API quota has been exceeded. Please wait and try again, "
                "or use a project with billing enabled."
            ) from e
        raise
    except errors.ServerError as e:
        if e.code == 503:
            raise RuntimeError(
                "I am currently experiencing high demand. Spikes in demand are usually temporary. Please try again later."
            ) from e
        raise
