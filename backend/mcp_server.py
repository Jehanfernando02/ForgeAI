"""
ForgeAI MCP Server — Phase 3

Exposes ForgeAI's tools through the Model Context Protocol.

MCP is a standardized protocol for AI models to access
tools and data sources. By implementing an MCP server,
ForgeAI's tools can be used by any MCP-compatible client —
not just LangChain agents.

Think of it like building a REST API for your tools —
instead of HTTP endpoints, you expose MCP tool definitions.

Run standalone:
    python backend/mcp_server.py

The server runs on port 8000 by default.
Your LangChain agents connect to it as an MCP client.
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from backend.tools.workout_tools import (
    log_workout, get_workout_history,
    calculate_one_rep_max, check_progressive_overload
)
from backend.tools.exercise_tools import search_exercises, get_exercise_details
from backend.tools.nutrition_tools import calculate_tdee, log_nutrition, get_nutrition_history
from backend.tools.user_tools import get_user_profile, update_user_profile, get_progress_metrics


# ── Tool definitions (MCP schema format) ─────────────────────

MCP_TOOLS = {
    "log_workout": {
        "description": "Save a completed workout session to the database",
        "function": log_workout,
        "parameters": {
            "user_id":   {"type": "string",  "required": True},
            "exercises": {"type": "array",   "required": True},
            "session_notes":          {"type": "string",  "required": False},
            "perceived_difficulty":   {"type": "string",  "required": False},
            "duration_minutes":       {"type": "integer", "required": False}
        }
    },
    "get_workout_history": {
        "description": "Retrieve past workouts for a user",
        "function": get_workout_history,
        "parameters": {
            "user_id":      {"type": "string",  "required": True},
            "days":         {"type": "integer", "required": False},
            "muscle_group": {"type": "string",  "required": False}
        }
    },
    "calculate_one_rep_max": {
        "description": "Estimate 1RM from a submaximal set using Epley formula",
        "function": calculate_one_rep_max,
        "parameters": {
            "weight_kg": {"type": "number",  "required": True},
            "reps":      {"type": "integer", "required": True}
        }
    },
    "check_progressive_overload": {
        "description": "Compare recent vs previous performance on an exercise",
        "function": check_progressive_overload,
        "parameters": {
            "user_id":       {"type": "string", "required": True},
            "exercise_name": {"type": "string", "required": True}
        }
    },
    "search_exercises": {
        "description": "Search exercise library by muscle group, equipment, difficulty",
        "function": search_exercises,
        "parameters": {
            "muscle_group":    {"type": "string", "required": False},
            "equipment":       {"type": "string", "required": False},
            "difficulty":      {"type": "string", "required": False},
            "movement_pattern":{"type": "string", "required": False}
        }
    },
    "get_exercise_details": {
        "description": "Get detailed information about a specific exercise",
        "function": get_exercise_details,
        "parameters": {
            "exercise_name": {"type": "string", "required": True}
        }
    },
    "calculate_tdee": {
        "description": "Calculate TDEE and macro targets using Mifflin-St Jeor",
        "function": calculate_tdee,
        "parameters": {
            "weight_kg":      {"type": "number",  "required": True},
            "height_cm":      {"type": "number",  "required": True},
            "age":            {"type": "integer", "required": True},
            "gender":         {"type": "string",  "required": True},
            "activity_level": {"type": "string",  "required": True},
            "goal":           {"type": "string",  "required": True}
        }
    },
    "log_nutrition": {
        "description": "Save a nutrition log entry for the user",
        "function": log_nutrition,
        "parameters": {
            "user_id": {"type": "string", "required": True},
            "meals":   {"type": "array",  "required": True},
            "notes":   {"type": "string", "required": False}
        }
    },
    "get_nutrition_history": {
        "description": "Retrieve past nutrition logs",
        "function": get_nutrition_history,
        "parameters": {
            "user_id": {"type": "string",  "required": True},
            "days":    {"type": "integer", "required": False}
        }
    },
    "get_user_profile": {
        "description": "Retrieve stored user profile",
        "function": get_user_profile,
        "parameters": {
            "user_id": {"type": "string", "required": True}
        }
    },
    "update_user_profile": {
        "description": "Update user profile with new information",
        "function": update_user_profile,
        "parameters": {
            "user_id": {"type": "string", "required": True}
        }
    },
    "get_progress_metrics": {
        "description": "Compute progress metrics from workout history",
        "function": get_progress_metrics,
        "parameters": {
            "user_id": {"type": "string",  "required": True},
            "days":    {"type": "integer", "required": False}
        }
    }
}


class MCPHandler(BaseHTTPRequestHandler):
    """
    Simple HTTP-based MCP server handler.

    Endpoints:
      GET  /tools        — list all available tools
      POST /tools/call   — execute a tool
      GET  /health       — server health check
    """

    def log_message(self, format, *args):
        pass  # Suppress default request logging

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/tools':
            tools_list = [
                {
                    "name": name,
                    "description": info["description"],
                    "parameters": info["parameters"]
                }
                for name, info in MCP_TOOLS.items()
            ]
            self.send_json({"tools": tools_list, "count": len(tools_list)})

        elif self.path == '/health':
            self.send_json({"status": "ok", "server": "ForgeAI MCP", "tools": len(MCP_TOOLS)})

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path == '/tools/call':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body   = json.loads(self.rfile.read(length))

                tool_name = body.get('tool')
                params    = body.get('params', {})

                if tool_name not in MCP_TOOLS:
                    self.send_json(
                        {"error": f"Unknown tool: {tool_name}"},
                        404
                    )
                    return

                func   = MCP_TOOLS[tool_name]["function"]
                result = func(**params)
                self.send_json({"result": result, "tool": tool_name})

            except Exception as e:
                self.send_json({"error": str(e)}, 500)
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def run_mcp_server(port: int = 8000):
    server = HTTPServer(('localhost', port), MCPHandler)
    print(f"\n  ForgeAI MCP Server running → http://localhost:{port}")
    print(f"  Tools available: {len(MCP_TOOLS)}")
    print(f"  GET  http://localhost:{port}/tools")
    print(f"  POST http://localhost:{port}/tools/call\n")
    server.serve_forever()


if __name__ == '__main__':
    run_mcp_server()
