import unittest
from unittest.mock import patch

import tools


SAMPLE_FLIGHTS = [
    {
        "flight_status": "scheduled",
        "departure": {
            "delay": 30,
            "scheduled": "2026-08-19T08:00:00+00:00",
        },
        "arrival": {
            "scheduled": "2026-08-19T15:00:00+00:00",
        },
        "airline": {"name": "Air One"},
    },
    {
        "flight_status": "cancelled",
        "departure": {
            "delay": 0,
            "cancelled": True,
            "scheduled": "2026-08-19T10:00:00+00:00",
        },
        "arrival": {
            "scheduled": "2026-08-19T12:00:00+00:00",
        },
        "airline": {"name": "Air Two"},
    },
]


class ToolSmokeTests(unittest.TestCase):
    @patch("tools._fetch_departing_flights", return_value=("TEST", SAMPLE_FLIGHTS))
    def test_expansion_score_is_deterministic(self, _fetch_flights):
        result = tools.calculate_expansion_score("TEST", "test-key")

        self.assertEqual(result["airport_code"], "TEST")
        self.assertEqual(result["congestion_percentage"], 50.0)
        self.assertEqual(result["average_delay_minutes"], 15.0)
        self.assertEqual(result["unique_airlines_in_sample"], 2)
        self.assertEqual(result["expansion_recommendation_score"], 51.5)
        self.assertEqual(_fetch_flights.call_count, 1)

    @patch("tools._fetch_departing_flights", return_value=("ANC", SAMPLE_FLIGHTS))
    def test_long_haul_uses_timestamps(self, _fetch_flights):
        result = tools.calculate_long_haul_percentage("ANC", "test-key")

        self.assertEqual(result["long_haul_percentage"], 50.0)
        self.assertEqual(result["classified_flights"], 2)
        self.assertEqual(result["scheduled_duration_flights"], 2)

    @patch("tools._fetch_departing_flights", return_value=("SFO", SAMPLE_FLIGHTS))
    def test_unmet_demand_pressure_includes_components(self, _fetch_flights):
        result = tools.assess_unmet_demand("SFO", "test-key")

        self.assertEqual(result["estimated_unmet_demand_pressure"], 41)
        self.assertEqual(result["delay_rate"], 50.0)
        self.assertEqual(result["cancellation_rate"], 50.0)
        self.assertEqual(
            set(result["score_components"]),
            {
                "delay_frequency_pressure",
                "delay_severity_pressure",
                "cancellation_pressure",
            },
        )

    @patch(
        "tools._fetch_departing_flights",
        return_value=(
            "TEST",
            [{"departure": None, "arrival": None, "airline": None}],
        ),
    )
    def test_malformed_nested_fields_do_not_crash(self, _fetch_flights):
        result = tools.calculate_expansion_score("TEST", "test-key")

        self.assertEqual(result["congestion_percentage"], 0.0)
        self.assertEqual(result["unique_airlines_in_sample"], 0)


if __name__ == "__main__":
    unittest.main()
