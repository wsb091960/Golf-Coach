(() => {
    "use strict";

    const form = document.getElementById("standalone-analysis-form");
    const status = document.getElementById("mcp-analysis-status");
    const output = document.getElementById("mcp-analysis-copy");
    const result = document.getElementById("mcp-analysis-result");
    if (!form || !status || !output || !result) return;

    function decodeResponse(response, raw) {
        const contentType = (response.headers.get("content-type") || "").toLowerCase();
        if (contentType.includes("text/event-stream")) {
            const data = raw.split(/\r?\n/)
                .filter(line => line.startsWith("data:"))
                .map(line => line.slice(5).trim())
                .filter(Boolean);
            const parsed = data.map(value => {
                try { return JSON.parse(value); } catch (_) { return null; }
            }).filter(Boolean);
            return parsed.find(item => item.result || item.error) || parsed[0] || {};
        }
        try { return JSON.parse(raw); } catch (_) { return {}; }
    }

    async function postMcp(payload, sessionId, protocolVersion) {
        const headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        };
        if (sessionId) headers["Mcp-Session-Id"] = sessionId;
        if (protocolVersion) headers["Mcp-Protocol-Version"] = protocolVersion;
        const response = await fetch("/mcp/", {
            method: "POST",
            headers,
            body: JSON.stringify(payload),
            credentials: "same-origin",
        });
        const raw = await response.text();
        const message = decodeResponse(response, raw);
        if (!response.ok || message.error) {
            const detail = message.error?.message || raw || `MCP request failed (${response.status})`;
            throw new Error(detail);
        }
        return { message, sessionId: response.headers.get("Mcp-Session-Id") || sessionId };
    }

    async function callTool(args) {
        const initialized = await postMcp({
            jsonrpc: "2.0",
            id: 1,
            method: "initialize",
            params: {
                protocolVersion: "2025-06-18",
                capabilities: {},
                clientInfo: { name: "WSBCO Golf Coach Simulator", version: "1.0" },
            },
        });
        const negotiatedVersion = initialized.message.result?.protocolVersion || "2025-06-18";
        await postMcp({ jsonrpc: "2.0", method: "notifications/initialized" }, initialized.sessionId, negotiatedVersion);
        const called = await postMcp({
            jsonrpc: "2.0",
            id: 2,
            method: "tools/call",
            params: { name: "analyze_simulator_shot", arguments: args },
        }, initialized.sessionId, negotiatedVersion);
        const content = called.message.result?.content || [];
        const textBlock = content.find(item => item.type === "text" && item.text);
        if (!textBlock) throw new Error("MCP returned no coaching analysis.");
        return textBlock.text;
    }

    form.addEventListener("submit", async event => {
        event.preventDefault();
        const submit = form.querySelector('button[type="submit"]');
        const data = new FormData(form);
        const args = {};
        const numeric = new Set([
            "ball_speed", "club_speed_estimate", "smash_factor", "launch_angle",
            "launch_direction", "club_face", "club_path", "face_to_path", "spin_rate",
            "spin_axis", "spin_axis_estimate", "carry_distance", "total_distance", "apex_height",
        ]);
        data.forEach((value, key) => {
            const trimmed = String(value).trim();
            if (!trimmed) return;
            args[key] = numeric.has(key) ? Number(trimmed) : trimmed;
        });
        status.textContent = "Sending current metrics to the standalone MCP coaching tool…";
        status.classList.remove("error");
        submit.disabled = true;
        try {
            const text = await callTool(args);
            output.textContent = text;
            result.classList.add("is-visible");
            status.textContent = "Analysis complete. The recommendation is based on the values and notes submitted above.";
            result.scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (error) {
            status.textContent = `Could not reach the simulator MCP tool: ${error.message}`;
            status.classList.add("error");
        } finally {
            submit.disabled = false;
        }
    });
})();
