#!/usr/bin/env python3
"""
Debug script to test Gemini API response format
"""

import sys
from pathlib import Path
import google.generativeai as genai
import json

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from utils.env_config import EnvConfig

def test_gemini_response():
    """Test basic Gemini response to understand the format"""
    
    # Load environment configuration
    env_config = EnvConfig()
    
    # Get API key from environment
    api_key = env_config.gemini_api_key
    if not api_key:
        print("❌ Cannot run debug without valid API key")
        print("💡 Please update your .env file with:")
        print("   GEMINI_API_KEY=your_actual_gemini_api_key")
        return False
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Simple function definition - correct format for Gemini
    functions = [
        {
            "name": "update_position",
            "description": "Update position in seismic view",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "x": {"type": "NUMBER", "description": "X position"},
                    "y": {"type": "NUMBER", "description": "Y position"},
                    "z": {"type": "NUMBER", "description": "Z position"}
                },
                "required": ["x", "y", "z"]
            }
        }
    ]
    
    # Test prompt
    prompt = "Move to crossline 165000, inline 115000, depth 4000"
    
    try:
        print("🧪 Testing Gemini API response format...")
        print(f"Prompt: {prompt}")
        
        # Generate response
        response = model.generate_content(
            prompt,
            tools=functions,
            tool_config={'function_calling_config': {'mode': 'ANY'}}
        )
        
        print("\n📋 Raw Response:")
        print(f"Type: {type(response)}")
        print(f"Response: {response}")
        
        print("\n📋 Response Candidates:")
        if hasattr(response, 'candidates'):
            print(f"Candidates: {len(response.candidates)}")
            for i, candidate in enumerate(response.candidates):
                print(f"  Candidate {i}: {candidate}")
                
                if hasattr(candidate, 'content'):
                    print(f"    Content: {candidate.content}")
                    
                    if hasattr(candidate.content, 'parts'):
                        print(f"    Parts: {len(candidate.content.parts)}")
                        for j, part in enumerate(candidate.content.parts):
                            print(f"      Part {j}: {part}")
                            print(f"      Part type: {type(part)}")
                            
                            if hasattr(part, 'function_call'):
                                print(f"        Function call: {part.function_call}")
                                if part.function_call:
                                    print(f"        Function name: {part.function_call.name}")
                                    print(f"        Function args: {part.function_call.args}")
                                    print(f"        Args type: {type(part.function_call.args)}")
                                    
                                    # Try to access args
                                    try:
                                        args_dict = dict(part.function_call.args)
                                        print(f"        Args as dict: {args_dict}")
                                    except Exception as e:
                                        print(f"        Error converting args: {e}")
        
        print("\n✅ Test completed")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_gemini_response()