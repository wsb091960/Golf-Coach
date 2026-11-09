# Standalone Simulator MCP Coaching

The simulator exposes a stateless MCP Streamable HTTP endpoint at `/mcp/` with one tool: `analyze_simulator_shot`.

The standalone simulator page is the MCP client. It submits the values currently displayed in Launch Inputs plus the optional handedness, coaching question, swing observations, P-position notes, sequencing, mobility, stability, and balance notes. It renders the tool's recommendation in the Coaching Analysis page. The payload is not linked to a student/session and does not read or write the database.

The response uses a numbered reference-guide layout: ball-flight read, six laws, coaching priority, teaching progression, fourteen principles, TGM/TPI/P-position cross-check, and a caution to individualize example numbers and feels.

The MCP tool is metric-led and deterministic. It does not call the OpenAI API or a ChatGPT model. Other MCP clients can connect to the same endpoint and use the tool result in their own model reasoning. The student/session routes continue to use the existing API-based `generate()` path.

The endpoint is unauthenticated because it accepts only explicitly supplied simulator metrics and coaching notes; it has no access to student, session, CRM, or saved swing data. Its permitted Host and Origin values are allowlisted in `app/mcp/simulator_server.py`.
