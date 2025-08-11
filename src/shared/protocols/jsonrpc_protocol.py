#!/usr/bin/env python3
"""
JSON-RPC Protocol for Tornado ↔ NLP Communication

This module defines the standard JSON-RPC 2.0 protocol for bidirectional
communication between the NLP system and Tornado listener.

Both directions use the same format for consistency.
"""

import json
import uuid
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 Request format"""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase"""
        result = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "id": self.id
        }
        if self.params is not None:
            result["params"] = self.params
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


@dataclass 
class JSONRPCResponse:
    """JSON-RPC 2.0 Response format"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase"""
        response = {
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }
        if self.result is not None:
            response["result"] = self.result
        if self.error is not None:
            response["error"] = self.error
        return response
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


@dataclass
class JSONRPCError:
    """JSON-RPC 2.0 Error format"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        error = {
            "code": self.code,
            "message": self.message
        }
        if self.data is not None:
            error["data"] = self.data
        return error


class JSONRPCProtocol:
    """JSON-RPC Protocol handler for Tornado ↔ NLP communication"""
    
    # Standard JSON-RPC error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # Custom error codes for Tornado
    TORNADO_ERROR = -32000
    BOOKMARK_ERROR = -32001
    VALIDATION_ERROR = -32002
    STATE_ERROR = -32003
    
    @staticmethod
    def create_request(method: str, params: Optional[Dict[str, Any]] = None, 
                      request_id: Optional[str] = None) -> JSONRPCRequest:
        """Create a JSON-RPC request"""
        return JSONRPCRequest(
            method=method,
            params=params,
            id=request_id or str(uuid.uuid4())
        )
    
    @staticmethod
    def create_success_response(request_id: str, result: Dict[str, Any]) -> JSONRPCResponse:
        """Create a successful JSON-RPC response"""
        return JSONRPCResponse(
            id=request_id,
            result=result
        )
    
    @staticmethod
    def create_error_response(request_id: str, code: int, message: str, 
                            data: Optional[Dict[str, Any]] = None) -> JSONRPCResponse:
        """Create an error JSON-RPC response"""
        error = JSONRPCError(code=code, message=message, data=data)
        return JSONRPCResponse(
            id=request_id,
            error=error.to_dict()
        )
    
    @staticmethod
    def parse_request(data: Union[str, Dict[str, Any]]) -> JSONRPCRequest:
        """Parse JSON-RPC request from string or dict"""
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}")
        
        if not isinstance(data, dict):
            raise ValueError("Request must be a JSON object")
        
        # Validate required fields
        if data.get("jsonrpc") != "2.0":
            raise ValueError("Invalid JSON-RPC version")
        
        if "method" not in data:
            raise ValueError("Missing method field")
        
        return JSONRPCRequest(
            jsonrpc=data["jsonrpc"],
            method=data["method"],
            params=data.get("params"),
            id=data.get("id")
        )
    
    @staticmethod
    def parse_response(data: Union[str, Dict[str, Any]]) -> JSONRPCResponse:
        """Parse JSON-RPC response from string or dict"""
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}")
        
        if not isinstance(data, dict):
            raise ValueError("Response must be a JSON object")
        
        # Validate required fields
        if data.get("jsonrpc") != "2.0":
            raise ValueError("Invalid JSON-RPC version")
        
        return JSONRPCResponse(
            jsonrpc=data["jsonrpc"],
            id=data.get("id"),
            result=data.get("result"),
            error=data.get("error")
        )


class TornadoStateProtocol:
    """Protocol for Tornado state updates and queries"""
    
    @staticmethod
    def create_state_update(current_params: Dict[str, Any], 
                           undo_redo_state: Dict[str, Any],
                           available_templates: list,
                           timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Create standardized state update"""
        return {
            "jsonrpc": "2.0",
            "method": "state_update",
            "params": {
                "curr_params": current_params,
                "undo_redo_state": undo_redo_state,
                "available_templates": available_templates,
                "timestamp": timestamp or datetime.utcnow().isoformat()
            },
            "id": str(uuid.uuid4())
        }
    
    @staticmethod
    def create_state_query(query_type: str, user_id: str) -> JSONRPCRequest:
        """Create state query request"""
        return JSONRPCProtocol.create_request(
            method="query_state",
            params={
                "query_type": query_type,  # "current_state", "templates", "undo_redo"
                "user_id": user_id
            }
        )
    
    @staticmethod
    def create_state_response(request_id: str, state_data: Dict[str, Any]) -> JSONRPCResponse:
        """Create state query response"""
        return JSONRPCProtocol.create_success_response(
            request_id=request_id,
            result={
                "state": state_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


def main():
    """Test the JSON-RPC protocol"""
    print("🧪 Testing JSON-RPC Protocol...")
    
    # Test request creation
    request = JSONRPCProtocol.create_request(
        method="update_position",
        params={"x": 165000, "y": 115000, "z": 4000}
    )
    print(f"Request: {request.to_json()}")
    
    # Test success response
    success_response = JSONRPCProtocol.create_success_response(
        request_id=request.id,
        result={
            "message": "Position updated successfully",
            "new_position": {"x": 165000, "y": 115000, "z": 4000},
            "current_state": {
                "can_undo": True,
                "undo_count": 3
            }
        }
    )
    print(f"Success Response: {success_response.to_json()}")
    
    # Test error response
    error_response = JSONRPCProtocol.create_error_response(
        request_id=request.id,
        code=JSONRPCProtocol.VALIDATION_ERROR,
        message="Invalid position parameters",
        data={"invalid_params": ["x", "y"]}
    )
    print(f"Error Response: {error_response.to_json()}")
    
    # Test state update
    state_update = TornadoStateProtocol.create_state_update(
        current_params={"x_position": 165000, "y_position": 115000},
        undo_redo_state={"can_undo": True, "undo_count": 3},
        available_templates=["default_view", "structural_analysis"]
    )
    print(f"State Update: {json.dumps(state_update, indent=2)}")
    
    print("JSON-RPC Protocol test completed")


if __name__ == "__main__":
    main()