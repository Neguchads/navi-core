"""Optional public-reference MCP server. No project paths, execution, persistence or network."""
from . import assist, nef
from .cli import NaviError

def create_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise NaviError("Optional MCP SDK not installed; install the reviewed mcp extra in an isolated environment") from exc
    server=FastMCP("NAVI Engineering Framework")
    @server.tool()
    def navi_profiles() -> dict:
        """List public NEF architecture profiles and verification capability labels."""
        return {"profiles":list(nef.standard()["profiles"]),"scope":"public reference only"}
    @server.tool()
    def navi_reference(profile: str) -> dict:
        """Get public engineering references for one explicit profile."""
        return nef.standard(profile)
    @server.tool()
    def navi_assist(profile: str) -> dict:
        """Get public instructions and contracts for any compatible host."""
        return assist.packet(profile)
    @server.tool()
    def navi_intake(brief: dict) -> dict:
        """Validate a structured brief without storing it. No execution or authorization."""
        return nef.intake(brief)
    @server.tool()
    def navi_handoff_check(handoff: dict) -> dict:
        """Validate structured handoff fields; self-reported evidence is not verified."""
        return assist.check_handoff(handoff)
    return server

def serve():
    create_server().run(transport="stdio")
