"""Bounded, read-only tool registry. No model-chosen URL, SQL or callable."""
from dataclasses import dataclass
from datetime import datetime, timezone
from time import monotonic
from typing import Any
from .config import GroundingError, RagUnavailable
from .diagnostics import event
from .tools import UpstreamError

@dataclass(frozen=True)
class ToolResult:
    name: str
    status: str
    data: Any = None
    reason: str | None = None
    fetched_at: str | None = None

    def evidence(self):
        return {"name":self.name,"status":self.status,"reason":self.reason,"fetchedAt":self.fetched_at}

class ToolRegistry:
    ALLOWED={"recommendation":"recommend","places":"amenity_map","market_summary":"market_summary"}
    def __init__(self,backend):self.backend=backend
    def execute(self,name,*args,**kwargs):
        if name not in self.ALLOWED:raise GroundingError("UNKNOWN_TOOL")
        operation=getattr(self.backend,self.ALLOWED[name],None)
        if not callable(operation):return ToolResult(name,"INSUFFICIENT_DATA",reason="TOOL_NOT_CONFIGURED")
        started=monotonic()
        try:
            data=operation(*args,**kwargs)
            if not isinstance(data,dict):raise GroundingError("INVALID_TOOL_RESULT")
            status="OK"
            if name=="recommendation" and not data.get("topProperties"):status="NO_MATCHES"
            elif name=="places" and not data.get("items"):status="NO_MATCHES"
            elif name=="market_summary" and data["overall"]["count"]==0:status="NO_MATCHES"
            result=ToolResult(name,status,data,fetched_at=datetime.now(timezone.utc).isoformat())
        except UpstreamError:
            result=ToolResult(name,"SOURCE_UNAVAILABLE",reason="UPSTREAM_ERROR")
        except RagUnavailable:
            result=ToolResult(name,"SOURCE_UNAVAILABLE",reason="SOURCE_NOT_READY")
        except GroundingError:
            result=ToolResult(name,"INVALID_EVIDENCE",reason="SOURCE_VALIDATION_FAILED")
        event("tool_result",tool=name,status=result.status,elapsedMs=round((monotonic()-started)*1000,1))
        return result
    def data(self,name,*args,**kwargs):
        result=self.execute(name,*args,**kwargs)
        if result.status=="INVALID_EVIDENCE":raise GroundingError("INVALID_TOOL_RESULT")
        if result.status in ("SOURCE_UNAVAILABLE","INSUFFICIENT_DATA"):raise UpstreamError()
        return result.data
