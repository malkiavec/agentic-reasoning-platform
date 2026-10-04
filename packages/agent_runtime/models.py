from typing import Any
from pydantic import BaseModel, ConfigDict, Field
class ContentPart(BaseModel):
    type:str; data:str; mime_type:str|None=None
class ToolCall(BaseModel):
    id:str; name:str; arguments:dict[str,Any]=Field(default_factory=dict)
class Usage(BaseModel):
    input_tokens:int=0; output_tokens:int=0; total_tokens:int=0
class ModelRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    input:list[ContentPart]; model:str; reasoning_effort:str="medium"
    tools:list[dict[str,Any]]=Field(default_factory=list)
    response_schema:dict[str,Any]|None=None; max_output_tokens:int|None=None
    metadata:dict[str,str]=Field(default_factory=dict)
class ModelResponse(BaseModel):
    model_config=ConfigDict(extra="forbid")
    output_text:str=""; tool_calls:list[ToolCall]=Field(default_factory=list)
    structured_output:dict[str,Any]|None=None; usage:Usage=Field(default_factory=Usage)
    finish_reason:str|None=None; provider_request_id:str|None=None
