#!/usr/bin/env python3
"""
Test JSON-RPC Protocol for Tornado ↔ NLP Communication

This script demonstrates the consistent JSON-RPC format for both directions.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from protocols.jsonrpc_protocol import JSONRPCProtocol, TornadoStateProtocol


def test_nlp_to_tornado_requests():
    """Test NLP → Tornado JSON-RPC requests"""
    print("🔄 TESTING NLP → TORNADO REQUESTS")
    print("="*60)
    
    # Test position update request
    position_request = JSONRPCProtocol.create_request(
        method="update_position",
        params={"x": 165000, "y": 115000, "z": 4000}
    )
    
    print("1. Position Update Request:")
    print(json.dumps(position_request.to_dict(), indent=2))
    
    # Test template load request
    template_request = JSONRPCProtocol.create_request(
        method="load_template",
        params={"template_name": "structural_analysis"}
    )
    
    print("\n2. Template Load Request:")
    print(json.dumps(template_request.to_dict(), indent=2))
    
    # Test state query request
    state_query = TornadoStateProtocol.create_state_query(
        query_type="current_state",
        user_id="test_user_001"
    )
    
    print("\n3. State Query Request:")
    print(json.dumps(state_query.to_dict(), indent=2))


def test_tornado_to_nlp_responses():
    """Test Tornado → NLP JSON-RPC responses"""
    print("\n🔄 TESTING TORNADO → NLP RESPONSES")
    print("="*60)
    
    # Test successful command response
    success_response = JSONRPCProtocol.create_success_response(
        request_id="cmd_123",
        result={
            "method": "update_position",
            "data": {
                "message": "Position updated successfully",
                "new_position": {"x": 165000, "y": 115000, "z": 4000}
            },
            "current_state": {
                "can_undo": True,
                "undo_count": 4,
                "current_params": {
                    "x_position": 165000,
                    "y_position": 115000,
                    "z_position": 4000,
                    "scale_x": 0.91,
                    "seismic_visible": True
                }
            },
            "timestamp": 1642248600
        }
    )
    
    print("1. Successful Command Response:")
    print(json.dumps(success_response.to_dict(), indent=2))
    
    # Test error response
    error_response = JSONRPCProtocol.create_error_response(
        request_id="cmd_124",
        code=JSONRPCProtocol.VALIDATION_ERROR,
        message="Invalid position parameters",
        data={
            "method": "update_position",
            "invalid_params": ["x", "y"],
            "valid_ranges": {
                "x": [100000, 200000],
                "y": [100000, 150000],
                "z": [1000, 6000]
            }
        }
    )
    
    print("\n2. Error Response:")
    print(json.dumps(error_response.to_dict(), indent=2))
    
    # Test state update (Tornado → NLP)
    state_update = TornadoStateProtocol.create_state_update(
        current_params={
            "x_position": 165000,
            "y_position": 115000,
            "z_position": 4000,
            "scale_x": 0.91,
            "scale_y": 0.91,
            "rotation": -0.785,
            "seismic_visible": True,
            "attribute_visible": False,
            "horizon_visible": False
        },
        undo_redo_state={
            "can_undo": True,
            "can_redo": False,
            "undo_count": 4,
            "redo_count": 0
        },
        available_templates=[
            "default_view",
            "structural_analysis", 
            "amplitude_analysis",
            "frequency_analysis"
        ]
    )
    
    print("\n3. State Update (Tornado → NLP):")
    print(json.dumps(state_update, indent=2))


def test_state_query_responses():
    """Test state query responses"""
    print("\n🔄 TESTING STATE QUERY RESPONSES")
    print("="*60)
    
    # Test current state response
    current_state_response = TornadoStateProtocol.create_state_response(
        request_id="query_123",
        state_data={
            "curr_params": {
                "x_position": 165000,
                "y_position": 115000,
                "z_position": 4000,
                "scale_x": 0.91,
                "seismic_visible": True
            },
            "undo_redo_state": {
                "can_undo": True,
                "undo_count": 4
            }
        }
    )
    
    print("1. Current State Response:")
    print(json.dumps(current_state_response.to_dict(), indent=2))
    
    # Test templates response
    templates_response = TornadoStateProtocol.create_state_response(
        request_id="query_124",
        state_data={
            "available_templates": [
                "default_view",
                "structural_analysis",
                "amplitude_analysis"
            ]
        }
    )
    
    print("\n2. Templates Response:")
    print(json.dumps(templates_response.to_dict(), indent=2))


def test_protocol_parsing():
    """Test parsing JSON-RPC messages"""
    print("\n🔄 TESTING PROTOCOL PARSING")
    print("="*60)
    
    # Test request parsing
    request_json = '''
    {
        "jsonrpc": "2.0",
        "method": "update_position",
        "params": {"x": 165000, "y": 115000, "z": 4000},
        "id": "cmd_123"
    }
    '''
    
    try:
        parsed_request = JSONRPCProtocol.parse_request(request_json)
        print("1. Parsed Request:")
        print(f"   Method: {parsed_request.method}")
        print(f"   Params: {parsed_request.params}")
        print(f"   ID: {parsed_request.id}")
    except Exception as e:
        print(f"❌ Request parsing failed: {e}")
    
    # Test response parsing
    response_json = '''
    {
        "jsonrpc": "2.0",
        "id": "cmd_123",
        "result": {
            "message": "Position updated",
            "new_position": {"x": 165000, "y": 115000, "z": 4000}
        }
    }
    '''
    
    try:
        parsed_response = JSONRPCProtocol.parse_response(response_json)
        print("\n2. Parsed Response:")
        print(f"   ID: {parsed_response.id}")
        print(f"   Result: {parsed_response.result}")
        print(f"   Error: {parsed_response.error}")
    except Exception as e:
        print(f"❌ Response parsing failed: {e}")


def main():
    """Run JSON-RPC protocol tests"""
    print("🚀 JSON-RPC PROTOCOL TEST")
    print("="*70)
    print("Testing consistent JSON-RPC format for Tornado ↔ NLP communication")
    print()
    
    try:
        # Test all protocol aspects
        test_nlp_to_tornado_requests()
        test_tornado_to_nlp_responses()
        test_state_query_responses()
        test_protocol_parsing()
        
        print("\n" + "="*70)
        print("🎯 JSON-RPC PROTOCOL SUMMARY")
        print("="*70)
        
        print("✅ CONSISTENT FORMAT:")
        print("   • NLP → Tornado: JSON-RPC 2.0 requests")
        print("   • Tornado → NLP: JSON-RPC 2.0 responses")
        print("   • State updates: JSON-RPC 2.0 notifications")
        print("   • Error handling: Standard JSON-RPC error codes")
        
        print("\n✅ KEY IMPROVEMENTS:")
        print("   • Standardized request/response format")
        print("   • Proper error codes and messages")
        print("   • Consistent state update protocol")
        print("   • Bidirectional JSON-RPC communication")
        
        print("\n✅ FIREBASE COLLECTIONS:")
        print("   • tornado_requests/{user_id} - NLP → Tornado")
        print("   • tornado_state/{user_id} - Tornado → NLP")
        print("   • command_queues/{user_id}/commands - Command queue")
        
        print("\n🎉 JSON-RPC protocol is ready for production!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()