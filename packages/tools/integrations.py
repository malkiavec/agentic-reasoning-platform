from __future__ import annotations
from typing import Any
from urllib.parse import quote
import httpx
from packages.security.credentials import credentials
from packages.security.ssrf import validate_url
from packages.tools.contracts import ToolAdapter, ToolContext, ToolSecurity

class SaaSAdapter(ToolAdapter):
    credential_name: str
    base_url: str
    name: str
    security = ToolSecurity(risk="medium", timeout_seconds=20.0, idempotent=True)
    def _token(self, context: ToolContext) -> str:
        token = credentials.get(context.tenant_id, self.credential_name)
        if not token: raise RuntimeError(f"{self.credential_name}_credential_not_configured")
        return token
    async def _request(self, method: str, url: str, token: str, *, body: Any=None, params: dict[str,Any]|None=None, headers: dict[str,str]|None=None) -> Any:
        h={"Accept":"application/json",**(headers or {})}
        if token: h.setdefault("Authorization",f"Bearer {token}")
        async with httpx.AsyncClient(timeout=self.security.timeout_seconds,follow_redirects=False) as c:
            r=await c.request(method,url,json=body,params=params,headers=h); r.raise_for_status()
            return r.json() if r.content else {"status_code":r.status_code}
    def is_idempotent(self,a:dict[str,Any])->bool: return str(a.get("method","GET")).upper() in {"GET","HEAD"}
    def _path(self,action:str,a:dict[str,Any])->str: raise NotImplementedError
    async def invoke(self,a:dict[str,Any],context:ToolContext)->Any:
        action=str(a.get("action","")).strip()
        if not action: raise ValueError("integration_action_required")
        return await self._request(str(a.get("method","GET")).upper(),self.base_url.rstrip()+"/"+self._path(action,a).lstrip("/"),self._token(context),body=a.get("body"),params=a.get("params"))

class GitLabAdapter(SaaSAdapter):
    name="gitlab"; credential_name="gitlab"; base_url="https://gitlab.com/api/v4"
    def _path(self,action,a):
        p=quote(str(a.get("project","")),safe="")
        m={"project":f"projects/{p}","issues":f"projects/{p}/issues","issue":f"projects/{p}/issues/{quote(str(a['issue_id']))}","merge_requests":f"projects/{p}/merge_requests","file":f"projects/{p}/repository/files/{quote(str(a['file_path']),safe='')}"}
        if action not in m: raise ValueError("unsupported_gitlab_action")
        return m[action]

class SlackAdapter(SaaSAdapter):
    name="slack"; credential_name="slack"; base_url="https://slack.com/api"; security=ToolSecurity(risk="medium",timeout_seconds=20,idempotent=False)
    def _path(self,action,a):
        m={"channels":"conversations.list","history":"conversations.history","post_message":"chat.postMessage","replies":"conversations.replies"}
        if action not in m: raise ValueError("unsupported_slack_action")
        return m[action]
    async def _request(self,method,url,token,**kw):
        return await super()._request(method,url,token,headers={"Authorization":f"Bearer {token}"},**{k:v for k,v in kw.items() if k!="headers"})

class DiscordAdapter(SaaSAdapter):
    name="discord"; credential_name="discord"; base_url="https://discord.com/api/v10"; security=ToolSecurity(risk="medium",timeout_seconds=20,idempotent=False)
    def _path(self,action,a):
        g=quote(str(a.get("guild_id",""))); c=quote(str(a.get("channel_id","")))
        m={"guild":f"guilds/{g}","channels":f"guilds/{g}/channels","messages":f"channels/{c}/messages","send_message":f"channels/{c}/messages"}
        if action not in m: raise ValueError("unsupported_discord_action")
        return m[action]
    async def _request(self,method,url,token,**kw):
        return await super()._request(method,url,"",headers={"Authorization":f"Bot {token}"},**{k:v for k,v in kw.items() if k!="headers"})

class GmailAdapter(SaaSAdapter):
    name="gmail"; credential_name="gmail"; base_url="https://gmail.googleapis.com/gmail/v1/users/me"; security=ToolSecurity(risk="high",timeout_seconds=20,idempotent=False)
    def _path(self,action,a):
        m={"messages":"messages","message":f"messages/{quote(str(a['message_id']))}","send":"messages/send","threads":"threads"}
        if action not in m: raise ValueError("unsupported_gmail_action")
        return m[action]

class GoogleDriveAdapter(SaaSAdapter):
    name="google_drive"; credential_name="google_drive"; base_url="https://www.googleapis.com/drive/v3"
    def _path(self,action,a):
        m={"files":"files","file":f"files/{quote(str(a['file_id']))}","permissions":f"files/{quote(str(a['file_id']))}/permissions"}
        if action not in m: raise ValueError("unsupported_google_drive_action")
        return m[action]

class NotionAdapter(SaaSAdapter):
    name="notion"; credential_name="notion"; base_url="https://api.notion.com/v1"; security=ToolSecurity(risk="medium",timeout_seconds=20,idempotent=False)
    def _path(self,action,a):
        m={"search":"search","query_database":f"databases/{quote(str(a['database_id']))}/query","page":f"pages/{quote(str(a['page_id']))}","database":f"databases/{quote(str(a['database_id']))}"}
        if action not in m: raise ValueError("unsupported_notion_action")
        return m[action]
    async def _request(self,method,url,token,**kw):
        return await super()._request(method,url,token,headers={"Notion-Version":"2022-06-28"},**{k:v for k,v in kw.items() if k!="headers"})

class LinearAdapter(SaaSAdapter):
    name="linear"; credential_name="linear"; base_url="https://api.linear.app"; security=ToolSecurity(risk="medium",timeout_seconds=20,idempotent=False)
    def _path(self,action,a):
        if action!="graphql": raise ValueError("unsupported_linear_action")
        return "graphql"
    async def invoke(self,a,context):
        q=str(a.get("query","")).strip()
        if not q: raise ValueError("linear_query_required")
        return await self._request("POST",self.base_url+"/graphql",self._token(context),body={"query":q,"variables":a.get("variables",{})})

class JiraAdapter(SaaSAdapter):
    name="jira"; credential_name="jira"; security=ToolSecurity(risk="medium",timeout_seconds=20,idempotent=True)
    def _path(self,action,a):
        m={"issue":f"issue/{quote(str(a['issue_key']))}","search":"search","projects":"project"}
        if action not in m: raise ValueError("unsupported_jira_action")
        return m[action]
    async def invoke(self,a,context):
        base=str(a.get("base_url","")).rstrip("/")
        validate_url(base)
        return await self._request(str(a.get("method","GET")).upper(),base+"/rest/api/3/"+self._path(str(a["action"]),a),self._token(context),body=a.get("body"),params=a.get("params"))

class DatabaseAdapter(ToolAdapter):
    name="databases"; security=ToolSecurity(risk="high",requires_approval=True,timeout_seconds=20,idempotent=True)
    async def invoke(self,a,context):
        dsn=credentials.get(context.tenant_id,"databases")
        if not dsn: raise RuntimeError("database_credential_not_configured")
        q=str(a.get("query","")).strip()
        if not q.lower().startswith(("select","with","show","describe","explain")): raise ValueError("database_read_only_query_required")
        import asyncpg
        conn=await asyncpg.connect(dsn=dsn,timeout=self.security.timeout_seconds)
        try: return [dict(r) for r in await conn.fetch(q,*(a.get("parameters") or []))]
        finally: await conn.close()

class WebhookAdapter(ToolAdapter):
    name="webhooks"; security=ToolSecurity(risk="high",requires_approval=True,timeout_seconds=20,idempotent=False)
    async def invoke(self,a,context):
        url=validate_url(str(a.get("url",""))); token=credentials.get(context.tenant_id,"webhooks")
        if not token: raise RuntimeError("webhook_credential_not_configured")
        method=str(a.get("method","POST")).upper()
        if method not in {"POST","PUT","PATCH"}: raise ValueError("webhook_method_not_allowed")
        h={"Authorization":f"Bearer {token}"}; h.update({str(k):str(v) for k,v in (a.get("headers") or {}).items() if str(k).lower() not in {"authorization","cookie","set-cookie"}})
        async with httpx.AsyncClient(timeout=self.security.timeout_seconds,follow_redirects=False) as c:
            r=await c.request(method,url,json=a.get("body"),headers=h); return {"status_code":r.status_code,"body":r.text[:100000]}

class MCPAdapter(ToolAdapter):
    name="mcp"; security=ToolSecurity(risk="high",requires_approval=True,timeout_seconds=30,idempotent=False)
    async def invoke(self,a,context):
        url=validate_url(str(a.get("url",""))); token=credentials.get(context.tenant_id,"mcp")
        if not token: raise RuntimeError("mcp_credential_not_configured")
        method=str(a.get("method","tools/call"))
        if not method.startswith("tools/"): raise ValueError("mcp_tool_method_required")
        payload={"jsonrpc":"2.0","id":context.request_id,"method":method,"params":a.get("params",{})}
        async with httpx.AsyncClient(timeout=self.security.timeout_seconds,follow_redirects=False) as c:
            r=await c.post(url,json=payload,headers={"Authorization":f"Bearer {token}"}); r.raise_for_status(); return r.json()

INTEGRATION_ADAPTERS={"gitlab":GitLabAdapter,"slack":SlackAdapter,"discord":DiscordAdapter,"gmail":GmailAdapter,"google_drive":GoogleDriveAdapter,"notion":NotionAdapter,"linear":LinearAdapter,"jira":JiraAdapter,"databases":DatabaseAdapter,"webhooks":WebhookAdapter,"mcp":MCPAdapter}
