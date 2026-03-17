"""
Claude tool-use agent for autonomous satellite imagery ordering.

The agent receives a watch (question + AOI + sensor preference) and:
1. Lists available analytics products
2. Searches the archive for suitable imagery
3. Estimates cost
4. Places the optimal order

The agent uses Claude's tool_use API feature — it reasons about which tools to
call and in what order, with no hardcoded decision logic.
"""
import json
from datetime import datetime, timedelta

import anthropic

from src.config import settings
from src.services.skyfi_client import SkyFiClient

_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=60.0)
_skyfi = SkyFiClient()

# --------------------------------------------------------------------------- #
# Tool definitions
# --------------------------------------------------------------------------- #

TOOLS: list[dict] = [
    {
        "name": "get_analytics_products",
        "description": (
            "List all available analytics products that can be applied to satellite imagery. "
            "Returns product IDs, descriptions, supported sensor types, and pricing. "
            "Always call this first so you know what analysis options are available."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_archive",
        "description": (
            "Search SkyFi's satellite image archive for imagery over an area of interest. "
            "Returns available images sorted by recency with resolution, price, cloud cover, and sensor type.\n\n"
            "SENSOR SELECTION RULES:\n"
            "- Maritime questions, vessel detection, cloudy regions → sensor_type='sar' (SAR works through clouds/night)\n"
            "- Vehicle counting, construction, visual change → sensor_type='optical'\n"
            "- Large area, low-budget, ~10m resolution acceptable → open_data_only=True (Sentinel-2, free)\n"
            "- If sensor_preference is 'auto', choose the best sensor for the question type\n\n"
            "For cloud-prone regions (North Sea, Pacific Northwest, tropics), prefer SAR even for visual questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "aoi_geojson": {
                    "type": "object",
                    "description": "GeoJSON Polygon geometry (pass the aoi exactly as provided)",
                },
                "date_from": {"type": "string", "description": "ISO 8601 date, e.g. 2024-01-01"},
                "date_to": {"type": "string", "description": "ISO 8601 date, e.g. 2024-12-31"},
                "sensor_type": {
                    "type": "string",
                    "enum": ["optical", "sar"],
                    "description": "Omit to search all sensor types",
                },
                "open_data_only": {
                    "type": "boolean",
                    "description": "If true, return only free Sentinel-2 open data",
                },
            },
            "required": ["aoi_geojson", "date_from", "date_to"],
        },
    },
    {
        "name": "estimate_cost",
        "description": (
            "Estimate the total cost (imagery + analytics) for an order before placing it. "
            "Always call this after selecting an image so the cost is logged."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "aoi_geojson": {"type": "object"},
                "sensor_type": {"type": "string", "enum": ["optical", "sar", "free"]},
                "analytics_type": {
                    "type": "string",
                    "description": "Analytics product ID (from get_analytics_products)",
                },
            },
            "required": ["aoi_geojson", "sensor_type"],
        },
    },
    {
        "name": "get_pass_predictions",
        "description": (
            "Get upcoming satellite pass predictions over the AOI. "
            "Call this if archive search returns no recent results, "
            "to tell the user when fresh imagery will be available."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "aoi_geojson": {"type": "object"},
                "days_ahead": {"type": "integer", "description": "How many days ahead to predict (default 7)"},
            },
            "required": ["aoi_geojson"],
        },
    },
    {
        "name": "place_order",
        "description": (
            "Place an order for a specific archive image with optional analytics. "
            "This is the final action — call it only after:\n"
            "1. Reviewing search results\n"
            "2. Selecting the best image for the question\n"
            "3. Estimating cost\n\n"
            "Choose analytics_type that best matches the question:\n"
            "- Counting vehicles/cars → vehicle_detection\n"
            "- Counting ships/vessels → vessel_detection\n"
            "- Construction/infrastructure change → change_detection\n"
            "- Water level/flood/reservoir → water_extent\n"
            "- Oil storage/commodity tracking → oil_tank_inventory\n"
            "- Building construction → building_extraction\n"
            "- Geological activity, volcanic features, terrain changes → change_detection\n"
            "- Wildlife, vegetation, land use → change_detection\n"
            "- Anything not covered above → change_detection (not vessel_detection)\n\n"
            "If no analytics product closely matches the question (e.g. the question is about "
            "geological features, wildlife, vegetation, or anything not covered by the available "
            "products), use change_detection as the generic fallback — it detects surface-level "
            "changes and can provide meaningful signal for almost any monitoring question. "
            "Do NOT use vessel_detection as a fallback for non-maritime questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "archive_id": {
                    "type": "string",
                    "description": "The image ID from search_archive results",
                },
                "analytics_type": {
                    "type": "string",
                    "description": "Analytics product ID. Omit only if no analytics product matches.",
                },
                "sensor_type": {
                    "type": "string",
                    "description": "The sensor type of the selected image (for logging)",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explain why you chose this image and analytics product",
                },
            },
            "required": ["archive_id", "reasoning", "sensor_type"],
        },
    },
]

# --------------------------------------------------------------------------- #
# System prompts
# --------------------------------------------------------------------------- #

ORDERING_SYSTEM = """You are Sentinel's Earth intelligence agent. Your mission is to autonomously answer questions about locations on Earth by selecting and ordering the optimal satellite imagery and analytics from the SkyFi platform.

You will be given:
- A natural language question about a location
- The area of interest as a GeoJSON polygon
- A sensor preference (auto/optical/sar/free)
- A date range to search

Your job:
1. Call get_analytics_products to understand what analysis is available
2. Call search_archive to find suitable imagery (consider: recency, resolution, sensor appropriateness, cloud cover, cost)
3. Call estimate_cost for the chosen image + analytics combination
4. Call place_order with your chosen image ID, analytics type, and a clear reasoning statement

Be decisive. Do not ask clarifying questions. Make the best possible choice with available data.
You must always end by calling place_order — that is the success condition."""

INTERPRETATION_SYSTEM = """You are interpreting satellite imagery analytics results to answer a plain-English question about a location on Earth.

You will receive:
- The original question
- The sensor type and capture timestamp of the imagery
- The raw analytics output from SkyFi

Guidelines for a high-quality answer:
- Write 2-4 sentences. Be direct and specific. Lead with the answer, not caveats.
- Cite the exact numbers from the analytics (counts, percentages, areas, volumes).
- Set confidence genuinely: "high" if the analytics type directly answers the question with strong numeric evidence; "medium" if the match is reasonable but indirect; "low" if the analytics type is mismatched with the question or the confidence score in the data is below 0.85.
- If the analytics type seems mismatched with the geography or question (e.g. vessel_detection ran over a desert, or building_extraction over open ocean), acknowledge this honestly: explain what was detected and note that the user should interpret results in geographic context.
- When the analytics type doesn't perfectly match the question (e.g. change_detection was used for a volcanic question, or vehicle_detection was used for a wildlife question), do NOT say the result is useless or should be disregarded. Instead, reason about what the data does tell you in the context of the question. Change detection percentages can indicate geological activity, vegetation shifts, or construction. Vehicle counts in remote areas can indicate human presence or equipment deployment. Water extent changes can proxy for flood or drought conditions. Always extract the most relevant signal from whatever data is available and frame it in terms of the original question. Only note the indirect nature of the measurement briefly, not as a disclaimer that invalidates the answer.
- SAR sensors cannot distinguish vehicle types; cloud cover may affect optical confidence. Note these caveats only when relevant.
- Do not hedge excessively. Report the data as a professional analyst would."""


# --------------------------------------------------------------------------- #
# Agent runner
# --------------------------------------------------------------------------- #

async def run_ordering_agent(watch: dict) -> dict:
    """
    Run the ordering agent for a watch.

    Args:
        watch: dict with keys: question, aoi (GeoJSON), sensor_preference

    Returns:
        dict with keys: skyfi_order_id, archive_id, sensor_type, analytics_type,
                        cost_usd, reasoning, agent_thoughts, error
    """
    today = datetime.utcnow().date().isoformat()
    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).date().isoformat()

    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"Question: {watch['question']}\n\n"
                f"Area of Interest (GeoJSON): {json.dumps(watch['aoi'])}\n"
                f"Sensor preference: {watch.get('sensor_preference', 'auto')}\n"
                f"Search date range: {thirty_days_ago} to {today}\n\n"
                "Please find the best satellite imagery and analytics to answer this question, "
                "then place the order."
            ),
        }
    ]

    result: dict = {
        "skyfi_order_id": None,
        "archive_id": None,
        "sensor_type": "optical",
        "analytics_type": None,
        "cost_usd": None,
        "reasoning": None,
        "agent_thoughts": [],
        "error": None,
    }

    for iteration in range(10):  # max 10 iterations
        try:
            response = await _client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=ORDERING_SYSTEM,
                tools=TOOLS,  # type: ignore[arg-type]
                messages=messages,
            )
        except Exception as e:
            result["error"] = f"Claude API error: {e}"
            break

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if not hasattr(block, "type") or block.type != "tool_use":
                continue

            tool_name: str = block.name
            tool_input: dict = block.input
            thought: dict = {
                "step": iteration,
                "toolCalled": tool_name,
                "toolInput": tool_input,
                "toolOutput": None,
            }

            try:
                if tool_name == "get_analytics_products":
                    output = await _skyfi.get_analytics_products()

                elif tool_name == "search_archive":
                    output = await _skyfi.search_archive(
                        aoi_geojson=tool_input["aoi_geojson"],
                        date_from=tool_input["date_from"],
                        date_to=tool_input["date_to"],
                        sensor_type=tool_input.get("sensor_type"),
                        open_data_only=tool_input.get("open_data_only", False),
                    )

                elif tool_name == "estimate_cost":
                    output = await _skyfi.estimate_cost(
                        aoi_geojson=tool_input["aoi_geojson"],
                        sensor_type=tool_input["sensor_type"],
                        analytics_type=tool_input.get("analytics_type"),
                    )
                    result["cost_usd"] = output.get("totalUsd")

                elif tool_name == "get_pass_predictions":
                    output = await _skyfi.get_pass_predictions(
                        aoi_geojson=tool_input["aoi_geojson"],
                        days_ahead=tool_input.get("days_ahead", 7),
                    )

                elif tool_name == "place_order":
                    order_resp = await _skyfi.place_archive_order(
                        archive_id=tool_input["archive_id"],
                        analytics_type=tool_input.get("analytics_type"),
                    )
                    result["skyfi_order_id"] = order_resp["orderId"]
                    result["archive_id"] = tool_input["archive_id"]
                    result["analytics_type"] = tool_input.get("analytics_type")
                    result["sensor_type"] = tool_input.get("sensor_type", "optical")
                    result["reasoning"] = tool_input.get("reasoning", "")
                    output = order_resp

                else:
                    output = {"error": f"Unknown tool: {tool_name}"}

                thought["toolOutput"] = output
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(output),
                })

            except Exception as e:
                error_output = {"error": str(e)}
                thought["toolOutput"] = error_output
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(error_output),
                    "is_error": True,
                })

            result["agent_thoughts"].append(thought)

        messages.append({"role": "user", "content": tool_results})

    if result["skyfi_order_id"] is None and result["error"] is None:
        result["error"] = "Agent completed without placing an order"

    return result


_SUBMIT_INTERPRETATION_TOOL: dict = {
    "name": "submit_interpretation",
    "description": "Submit the structured interpretation of the satellite analytics result.",
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "2-4 sentence plain-English answer to the question",
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
            },
            "evidence": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["count", "comparison", "detection", "measurement"],
                        },
                        "description": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["type", "description"],
                },
            },
        },
        "required": ["answer", "confidence", "evidence"],
    },
}


async def interpret_result(
    question: str,
    analytics_result: dict,
    sensor_type: str,
    captured_at: str | None,
) -> dict:
    """
    Use Claude to write a plain-English answer from raw SkyFi analytics output.

    Uses tool-use with tool_choice="any" to force structured output — more
    reliable than instruction-following JSON generation.

    Returns dict with: answer, confidence, evidence
    """
    prompt = (
        f"Question: {question}\n\n"
        f"Imagery: {sensor_type} sensor, captured {captured_at or 'recently'}\n\n"
        f"Analytics result:\n{json.dumps(analytics_result, indent=2)}"
    )
    try:
        response = await _client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=INTERPRETATION_SYSTEM,
            tools=[_SUBMIT_INTERPRETATION_TOOL],  # type: ignore[list-item]
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": prompt}],
        )
        for block in response.content:
            if hasattr(block, "type") and block.type == "tool_use":
                return block.input  # type: ignore[return-value]
        # Fallback: no tool_use block returned (should not happen with tool_choice="any")
        raise ValueError("No tool_use block in response")
    except Exception as e:
        return {
            "answer": f"Analytics processing complete. Raw result: {json.dumps(analytics_result)}",
            "confidence": "low",
            "evidence": [],
            "error": str(e),
        }
