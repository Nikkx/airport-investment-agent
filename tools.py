from datetime import datetime
import requests


class AviationstackError(RuntimeError):
    """Raised when Aviationstack cannot provide usable flight data."""


LONG_HAUL_THRESHOLD_HOURS = 6
BASE_EXPANSION_SCORE = 40
MAX_DELAY_SCORE = 30
MAX_DIVERSITY_SCORE = 30


def _nested_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _delay_minutes(flights: list[dict[str, object]]) -> list[int | float]:
    delays = [
        _nested_dict(flight.get("departure")).get("delay")
        for flight in flights
    ]
    return [delay for delay in delays if isinstance(delay, (int, float))]


def _fetch_departing_flights(
    airport_code: str,
    api_key: str | None,
) -> tuple[str, list[dict[str, object]]]:
    if not api_key:
        raise AviationstackError("Aviationstack API key is required.")

    code = airport_code.strip().upper()
    response = requests.get(
        "https://api.aviationstack.com/v1/flights",
        params={"access_key": api_key, "dep_iata": code, "limit": 100},
        timeout=30,
    )
    response.raise_for_status()
    api_data = response.json()

    if not isinstance(api_data, dict):
        raise AviationstackError("Aviationstack returned an invalid response.")

    api_error = api_data.get("error")
    if api_error:
        message = (
            api_error.get("message", "Aviationstack returned an unknown error.")
            if isinstance(api_error, dict)
            else str(api_error)
        )
        raise AviationstackError(message)

    flights = api_data.get("data", [])
    if not isinstance(flights, list) or not all(
        isinstance(flight, dict) for flight in flights
    ):
        raise AviationstackError("Aviationstack returned invalid flight data.")
    if not flights:
        raise AviationstackError(f"No live flight data available for {code} right now.")

    return code, flights


def calculate_expansion_score(
    airport_code: str,
    api_key: str | None = None,
) -> dict[str, object]:
    """Calculate an investment-pressure score from a live flight sample."""

    try:
        code, flights = _fetch_departing_flights(airport_code, api_key)
    except (requests.RequestException, ValueError) as exc:
        raise AviationstackError(f"Aviationstack request failed: {exc}") from exc

    total_flights = len(flights)

    delay_minutes = _delay_minutes(flights)
    avg_delay = sum(delay_minutes) / len(delay_minutes) if delay_minutes else 0

    airlines = {
        _nested_dict(flight.get("airline")).get("name")
        for flight in flights
        if _nested_dict(flight.get("airline")).get("name")
    }

    delayed_flights = sum(delay > 0 for delay in delay_minutes)
    congestion_percent = (delayed_flights / total_flights) * 100
    delay_score = min(MAX_DELAY_SCORE, avg_delay * 0.5)
    diversity_score = min(MAX_DIVERSITY_SCORE, len(airlines) * 2.0)
    final_score = round(BASE_EXPANSION_SCORE + delay_score + diversity_score, 1)

    return {
        "airport_code": code,
        "congestion_percentage": round(congestion_percent, 1),
        "average_delay_minutes": round(avg_delay, 1),
        "unique_airlines_in_sample": len(airlines),
        "sample_size": total_flights,
        "expansion_recommendation_score": final_score,
        "score_basis": "Live Aviationstack flight sample",
        "assumptions": [
            "The live sample is used as a proxy for operational pressure.",
            f"A {BASE_EXPANSION_SCORE}-point base prevents off-peak samples from collapsing the score.",
            "Average delay and airline diversity are treated as investment-pressure indicators.",
        ],
    }


def calculate_long_haul_percentage(
    airport_code: str,
    api_key: str | None = None,
) -> dict[str, object]:
    """Estimate long-haul share from Aviationstack departure and arrival times."""
    try:
        code, flights = _fetch_departing_flights(airport_code, api_key)
    except (requests.RequestException, ValueError) as exc:
        raise AviationstackError(f"Aviationstack request failed: {exc}") from exc

    long_haul_count = 0
    classified_count = 0
    scheduled_duration_count = 0
    for flight in flights:
        departure = _nested_dict(flight.get("departure"))
        arrival = _nested_dict(flight.get("arrival"))
        duration_hours = None

        for timestamp_name in ("actual", "estimated", "scheduled"):
            departure_time = departure.get(timestamp_name)
            arrival_time = arrival.get(timestamp_name)
            if not departure_time or not arrival_time:
                continue
            try:
                duration_hours = (
                    datetime.fromisoformat(arrival_time)
                    - datetime.fromisoformat(departure_time)
                ).total_seconds() / 3600
            except (TypeError, ValueError):
                continue
            if duration_hours >= 0:
                if timestamp_name == "scheduled":
                    scheduled_duration_count += 1
                break

        if duration_hours is not None:
            classified_count += 1
            long_haul_count += duration_hours >= LONG_HAUL_THRESHOLD_HOURS

    if classified_count == 0:
        raise AviationstackError(
            "Aviationstack's flight response does not include usable departure "
            "and arrival timestamps, so long-haul percentage cannot be estimated."
        )

    return {
        "airport_code": code,
        "long_haul_percentage": round(long_haul_count / classified_count * 100, 1),
        "long_haul_definition": (
            f"Estimated flight duration of at least {LONG_HAUL_THRESHOLD_HOURS} hours"
        ),
        "classified_flights": classified_count,
        "sample_size": len(flights),
        "scheduled_duration_flights": scheduled_duration_count,
        "estimation_basis": (
            "Actual, estimated, or scheduled departure and arrival timestamps"
        ),
    }


def assess_unmet_demand(
    airport_code: str,
    api_key: str | None = None,
) -> dict[str, object]:
    """Estimate demand pressure from live delays and cancellations."""
    try:
        code, flights = _fetch_departing_flights(airport_code, api_key)
    except (requests.RequestException, ValueError) as exc:
        raise AviationstackError(f"Aviationstack request failed: {exc}") from exc

    total_flights = len(flights)
    delay_minutes = _delay_minutes(flights)
    delayed_flights = sum(delay > 0 for delay in delay_minutes)
    cancelled_flights = sum(
        flight.get("flight_status") == "cancelled"
        or _nested_dict(flight.get("departure")).get("cancelled") is True
        for flight in flights
    )

    delay_rate = delayed_flights / total_flights
    cancellation_rate = cancelled_flights / total_flights
    average_delay = sum(delay_minutes) / len(delay_minutes) if delay_minutes else 0

    delay_frequency_pressure = min(35, delay_rate * 100 * 0.35)
    delay_severity_pressure = min(35, average_delay / 60 * 35)
    cancellation_pressure = min(30, cancellation_rate * 100 * 0.30)
    estimated_pressure = round(
        delay_frequency_pressure
        + delay_severity_pressure
        + cancellation_pressure
    )

    return {
        "airport_code": code,
        "estimated_unmet_demand_pressure": estimated_pressure,
        "delay_rate": round(delay_rate * 100, 1),
        "average_delay_minutes": round(average_delay, 1),
        "cancellation_rate": round(cancellation_rate * 100, 1),
        "sample_size": total_flights,
        "score_components": {
            "delay_frequency_pressure": round(delay_frequency_pressure, 1),
            "delay_severity_pressure": round(delay_severity_pressure, 1),
            "cancellation_pressure": round(cancellation_pressure, 1),
        },
        "proxy_basis": "Estimated from Aviationstack live operational data",
        "explanation": (
            "This exercise estimate uses delay frequency, average delay severity, "
            "and cancellation rate. It is not measured passenger demand because "
            "Aviationstack does not provide bookings, denied boarding, or "
            "unconstrained schedules."
        ),
    }
