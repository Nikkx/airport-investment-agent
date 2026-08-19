import requests


class AviationstackError(RuntimeError):
    """Raised when Aviationstack cannot provide usable flight data."""


def calculate_expansion_score(
    airport_code: str,
    api_key: str | None = None,
) -> dict[str, object]:
    """
    Calculates the expansion score and metrics using live Aviationstack API data.
    Args: 
        airport_code (str): The 3-letter uppercase IATA code (e.g. LAX).
        api_key (str, optional): The Aviationstack API key.
    """

    if not api_key:
        raise AviationstackError("Aviationstack API key is required.")
    
    code = airport_code.strip().upper()
    url = "https://api.aviationstack.com/v1/flights"
    params = {
        "access_key": api_key,
        "dep_iata": code,
        "limit": 100,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        api_data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise AviationstackError(f"Aviationstack request failed: {exc}") from exc

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

    total_flights = len(flights)

    if total_flights == 0:
        raise AviationstackError(f"No live flight data available for {code} right now.")

    delay_minutes = [
        flight.get("departure", {}).get("delay")
        for flight in flights
        if isinstance(flight.get("departure", {}).get("delay"), (int, float))
    ]
    avg_delay = sum(delay_minutes) / len(delay_minutes) if delay_minutes else 0

    airlines = {
        flight.get("airline", {}).get("name")
        for flight in flights
        if flight.get("airline", {}).get("name")
    }

    delayed_flights = sum(delay > 0 for delay in delay_minutes)
    congestion_percent = (delayed_flights / total_flights) * 100
    delay_score = min(30, avg_delay * 0.5)
    diversity_score = min(30, len(airlines) * 2.0)
    final_score = round(40 + delay_score + diversity_score, 1)

    return {
        "airport_code": code,
        "congestion_percentage": round(congestion_percent, 1),
        "average_delay_minutes": round(avg_delay, 1),
        "unique_airlines_in_sample": len(airlines),
        "sample_size": total_flights,
        "expansion_recommendation_score": final_score,
        "score_basis": "Live Aviationstack flight sample",
    }
