"""Stateless MCP endpoint for standalone ball-flight coaching."""
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.services.simulator_mcp_coaching import analyze_simulator_swing

mcp = FastMCP(
    "WSBCO Golf Coach Simulator",
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        allowed_hosts=[
            "wsbco-golf-coach.onrender.com",
            "golf.busterball.com",
            "busterball.com",
            "www.busterball.com",
        ],
        allowed_origins=[
            "https://wsbco-golf-coach.onrender.com",
            "https://golf.busterball.com",
            "https://busterball.com",
            "https://www.busterball.com",
        ],
    ),
)


@mcp.tool()
def analyze_simulator_shot(
    ball_speed: float | None = None,
    club_speed_estimate: float | None = None,
    smash_factor: float | None = None,
    launch_angle: float | None = None,
    launch_direction: float | None = None,
    club_face: float | None = None,
    club_path: float | None = None,
    face_to_path: float | None = None,
    spin_rate: float | None = None,
    spin_axis: float | None = None,
    spin_axis_estimate: float | None = None,
    carry_distance: float | None = None,
    total_distance: float | None = None,
    apex_height: float | None = None,
    handedness: str = "right-handed",
    coaching_question: str = "",
    swing_observations: str = "",
    p_positions: str = "",
    sequencing: str = "",
    mobility: str = "",
    stability: str = "",
    balance: str = "",
) -> str:
    """Analyze only submitted simulator metrics and return a doc-style lesson plan.

    No student, session, CRM, or saved swing records are read or changed.
    """
    metrics = {
        "ball_speed": ball_speed,
        "club_speed_estimate": club_speed_estimate,
        "smash_factor": smash_factor,
        "launch_angle": launch_angle,
        "launch_direction": launch_direction,
        "club_face": club_face,
        "club_path": club_path,
        "face_to_path": face_to_path,
        "spin_rate": spin_rate,
        "spin_axis": spin_axis,
        "spin_axis_estimate": spin_axis_estimate,
        "carry_distance": carry_distance,
        "total_distance": total_distance,
        "apex_height": apex_height,
    }
    result = analyze_simulator_swing(
        metrics,
        handedness=handedness,
        coaching_question=coaching_question,
        swing_observations=swing_observations,
        p_positions=p_positions,
        sequencing=sequencing,
        mobility=mobility,
        stability=stability,
        balance=balance,
    )
    return result["analysis"]


# The endpoint accepts only explicitly supplied shot values and coaching notes.
# It has no database access and is deliberately independent of owner/session auth.
http_app = mcp.streamable_http_app()
