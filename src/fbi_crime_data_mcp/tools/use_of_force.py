"""Use of Force (UOF) data tool."""

from fastmcp import Context

from ..api_client import AppContext
from ..server import mcp
from ..validators import validate_state


@mcp.tool()
async def get_use_of_force_data(
    report_type: str,
    year: int | None = None,
    location: str | None = None,
    group: str | None = None,
    quarter: int | None = None,
    spec: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Get use of force data from law enforcement agencies. Covers incidents resulting in death, serious bodily injury, or firearm discharge.

    Args:
        report_type: "summary" for participation/submission data, "questions" for detailed question data, "reports" for report data
        year: Year for the data. Required for "summary" and "questions" types.
        location: "national" or a two-letter state abbreviation. Required for "summary" type.
        group: Group identifier for "questions" or "reports" types.
        quarter: Quarter (1-4) for "questions" type.
        spec: Report specification for "reports" type.
    """
    if report_type not in ("summary", "questions", "reports"):
        return "Invalid report_type. Must be 'summary', 'questions', or 'reports'."

    app_ctx: AppContext = ctx.lifespan_context

    if report_type == "summary":
        if year is None or not location:
            return "Both 'year' and 'location' are required for summary type."
        if location != "national":
            err = validate_state(location)
            if err:
                return f"Invalid location '{location}'. Must be 'national' or a state abbreviation."
        loc = location if location == "national" else location.upper()
        return await app_ctx.api_get("/uof", {"year": str(year), "location": loc})

    elif report_type == "questions":
        if not group or year is None or quarter is None:
            return "Parameters 'group', 'year', and 'quarter' are required for questions type."
        if not (1 <= quarter <= 4):
            return "Parameter 'quarter' must be between 1 and 4."
        return await app_ctx.api_get(f"/uof/questions/{group}/{year}/{quarter}")

    else:  # reports
        if not group or not spec:
            return "Parameters 'group' and 'spec' are required for reports type."
        return await app_ctx.api_get(f"/uof/reports/{group}/{spec}")
