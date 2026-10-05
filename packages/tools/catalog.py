from packages.tools.builtins import ApprovalProbeAdapter, EchoAdapter
from packages.tools.http_rest import HttpRestAdapter
from packages.tools.web_search import WebSearchAdapter
from packages.tools.github import GitHubAdapter, GitHubWriteAdapter
from packages.tools.integrations import INTEGRATION_ADAPTERS
from packages.tools.registry import ToolRegistry, ToolSpec

_GENERIC={"type":"object","properties":{"action":{"type":"string","minLength":1,"maxLength":100},"method":{"type":"string","enum":["GET","POST","PUT","PATCH","DELETE","HEAD"]},"project":{"type":"string","maxLength":256},"issue_id":{"type":["string","integer"]},"file_path":{"type":"string","maxLength":1000},"channel":{"type":"string","maxLength":256},"channel_id":{"type":"string","maxLength":256},"guild_id":{"type":"string","maxLength":256},"message_id":{"type":"string","maxLength":256},"page_id":{"type":"string","maxLength":256},"database_id":{"type":"string","maxLength":256},"issue_key":{"type":"string","maxLength":256},"base_url":{"type":"string","maxLength":2048},"query":{"type":"string","maxLength":100000},"variables":{"type":"object"},"params":{"type":"object"},"parameters":{"type":"array","maxItems":100},"body":{},"url":{"type":"string","maxLength":2048},"headers":{"type":"object","additionalProperties":{"type":"string"}}},"required":["action"],"additionalProperties":False}

def build_default_registry()->ToolRegistry:
    r=ToolRegistry()
    r.register(ToolSpec("echo","Return text without external side effects",{"type":"object","properties":{"text":{"type":"string","maxLength":10000}},"required":["text"],"additionalProperties":False}),EchoAdapter())
    r.register(ToolSpec("approval_probe","Test an approval-gated action",{"type":"object","properties":{"action":{"type":"string","maxLength":10000}},"required":["action"],"additionalProperties":False}),ApprovalProbeAdapter())
    r.register_external("web.search","Search the public web through the configured search provider",WebSearchAdapter(),input_schema={"type":"object","properties":{"query":{"type":"string","minLength":1,"maxLength":2000},"count":{"type":"integer","minimum":1,"maximum":20}},"required":["query"],"additionalProperties":False})
    r.register_external("github","Read GitHub repositories, files, issues, and code",GitHubAdapter(),input_schema={"type":"object","properties":{"action":{"type":"string","enum":["get_repository","list_issues","get_file","search_code"]},"owner":{"type":"string","maxLength":100},"repo":{"type":"string","maxLength":100},"path":{"type":"string","maxLength":1000},"ref":{"type":"string","maxLength":256},"query":{"type":"string","maxLength":1000},"state":{"type":"string","enum":["open","closed","all"]},"per_page":{"type":"integer","minimum":1,"maximum":100}},"required":["action"],"additionalProperties":False})
    r.register_external("github.write","Write to GitHub; always requires human approval",GitHubWriteAdapter(),input_schema={"type":"object","properties":{"owner":{"type":"string","maxLength":100},"repo":{"type":"string","maxLength":100},"method":{"type":"string","enum":["POST","PATCH","PUT","DELETE"]},"path":{"type":"string","maxLength":1000},"body":{}},"required":["owner","repo","method","path"],"additionalProperties":False})
    r.register_external("http.rest","Perform an outbound HTTP request through the SSRF and egress boundary",HttpRestAdapter(),input_schema={"type":"object","properties":{"method":{"type":"string","enum":["GET","HEAD","POST","PUT","PATCH","DELETE"]},"url":{"type":"string","maxLength":2048},"headers":{"type":"object","additionalProperties":{"type":"string"}},"json":{},"timeout_seconds":{"type":"number","minimum":0.1,"maximum":20}},"required":["url"],"additionalProperties":False},permissions=frozenset({"network.egress"}))
    for name,cls in INTEGRATION_ADAPTERS.items(): r.register_external(name,f"Production {name} integration",cls(),input_schema=_GENERIC)
    return r

EXTERNAL_TOOL_FAMILIES=("web.search","github","github.write","gitlab","slack","discord","gmail","google_drive","notion","linear","jira","databases","http.rest","webhooks","mcp")
