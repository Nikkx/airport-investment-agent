# Airport Investment Agent

**Setup Instructions:**
To run this application locally, you must provide your own Gemini and Aviationstack API keys. Create a `.streamlit/secrets.toml` file at the root of the project and add both keys:

```toml
GEMINI_API_KEY = "your_gemini_key_here"
AVIATIONSTACK_KEY = "your_aviationstack_key_here"
```

**Run the App:**
From the project root, run:

```bash
streamlit run main.py
```

**Run Tests:**
From the project root, run:

```bash
python -m unittest discover -s tests -v
```

## Capabilities and Scope

- **Deterministic scoring:** Airport expansion scores are calculated by Python tools using live Aviationstack flight data. The language model explains and compares those results; it does not invent the score.
- **Chat interface:** The Streamlit chat interface supports follow-up questions using the current conversation context.
- **Assumptions and uncertainty:** Scores use a live sample of up to 100 flights. Delay frequency, average delay, and airline diversity are proxies for investment pressure, not direct measures of profitability or passenger demand.
- **Estimated demand pressure:** Unmet-demand pressure is an exercise estimate based on operational delays and cancellations. Aviationstack does not provide bookings or truly unconstrained demand.
- **Long-haul estimates:** Long-haul percentages are estimated from available departure and arrival timestamps, using a six-hour duration threshold.

## Design and Architecture

The design separates the Streamlit chat interface, Gemini's conversational orchestration, and Python tools that retrieve public aviation data and perform deterministic calculations.

### Scoring Methodology

The expansion recommendation score is calculated deterministically in Python from a live Aviationstack sample of up to 100 departing flights:

- **Base score:** 40 points, providing a mathematical floor during off-peak periods.
- **Delay severity:** Up to 30 points based on average delay minutes.
- **Airline diversity:** Up to 30 points based on the number of unique airlines in the sample.

The resulting score ranges from 40 to 100 and represents investment pressure, not guaranteed profitability.

Estimated unmet-demand pressure uses a separate 0-to-100 exercise score based on delay frequency, delay severity, and cancellations. Long-haul percentage is estimated from available departure and arrival timestamps.

### Key Tradeoffs

- **Live data versus stability:** Current flight data is timely but can vary by time of day and does not represent long-term airport performance.
- **Simple KPI model versus completeness:** Delay and airline-diversity metrics are transparent and reproducible, but they do not include passenger volume, fares, bookings, seats, or historical trends.
- **Free API access versus coverage:** The sample is limited to the records and fields available through the Aviationstack plan, which can limit statistical reliability and available route details.
- **Single API versus richer data:** Because of time constraints, this exercise uses only the Aviationstack API. A production version should combine multiple public data sources, such as Aviationstack for live operations and BTS data for passenger, seat, and historical capacity metrics. This would improve estimates such as unmet flight demand.
- **Estimated demand versus measured demand:** Operational disruption can indicate pressure, but the application cannot observe passengers who wanted to fly but could not book.
- **Fixed long-haul threshold:** The six-hour long-haul threshold is an arbitrary, hardcoded exercise assumption rather than a universal aviation standard.
- **Free-tier AI latency:** Using a free-tier AI model can introduce quota limits, throttling, or delays in responses. A production version may require a higher-capacity model or paid API plan.

### Where AI Is Used

Gemini powers the conversational agent. It:

- Interprets natural-language airport and city references.
- Selects the appropriate public-data tool.
- Resolves follow-up references using the conversation history.
- Compares airports and explains rankings using returned KPIs.
- Communicates assumptions, uncertainty, and scope.

Python tools remain responsible for API requests, data validation, deterministic calculations, and score generation. Gemini explains the results but does not invent or replace the underlying scores.
