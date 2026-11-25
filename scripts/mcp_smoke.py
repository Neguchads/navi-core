"""Real SDK client/server stdio smoke; no AI host or credentials required."""
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params=StdioServerParameters(command=sys.executable,args=["-I","-m","navi_core","mcp"])
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            tools=await session.list_tools()
            names={tool.name for tool in tools.tools}
            assert names=={"navi_profiles","navi_reference","navi_assist","navi_intake","navi_handoff_check"},names
            for name,args in (("navi_profiles",{}),("navi_reference",{"profile":"game-recomp"}),
                              ("navi_assist",{"profile":"documentation"})):
                result=await session.call_tool(name,arguments=args)
                assert not result.isError,result
            result=await session.call_tool("navi_intake",arguments={"brief":{
                "schema_version":1,"goal":"","deliverable":"CSV","complexity":"nontrivial","acceptance":[],
                "constraints_state":"unknown","ambiguity":"material","questions":[],"risk":"low","approved":False}})
            assert not result.isError and "clarify" in str(result),result
            print("MCP SDK stdio smoke passed; public tools only")

if __name__=="__main__":
    asyncio.run(main())
