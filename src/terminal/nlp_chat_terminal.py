#!/usr/bin/env python3
"""
Natural Language Processing Chat Terminal for Seismic Navigation

This module provides a conversational terminal interface that uses Gemini API
to parse natural language commands into JSON-RPC format for seismic navigation.

Features:
- Natural language command processing
- Follow-up questions for ambiguous commands
- Context awareness and conversation history
- Parameter validation and guardrails
- Integration with Firebase command queue
- Real-time feedback and status updates
"""

import sys
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from nlp.gemini_command_parser import GeminiCommandParser
from firebase.firebase_config import FirebaseConfig, CommandQueueManager
from utils.env_config import EnvConfig


class NLPChatTerminal:
    """Natural Language Processing chat terminal for seismic navigation"""
    
    def __init__(self, gemini_api_key: str, enable_html_monitor: bool = False):
        """Initialize NLP chat terminal"""
        self.gemini_api_key = gemini_api_key
        self.enable_html_monitor = enable_html_monitor
        self.parser = None
        self.firebase_config = None
        self.queue_manager = None
        self.html_monitor = None
        self.connected = False
        self.running = False
        
        # Initialize components
        self.initialize_components()
        
    def initialize_components(self) -> bool:
        """Initialize Gemini parser and Firebase connection"""
        try:
            print("🤖 Initializing Seismic Navigation AI Assistant...")
            
            # Initialize Firebase first
            print("🔥 Connecting to Firebase...")
            self.firebase_config = FirebaseConfig()
            if not self.firebase_config.initialize_firebase():
                print("❌ Firebase connection failed - commands will not be sent to Tornado")
                self.connected = False
                self.firebase_config = None
            else:
                self.connected = True
                print("✅ Firebase connected - ready to send commands to Tornado")
            
            # Initialize Gemini parser with Firebase config
            print("🧠 Loading Gemini AI model...")
            self.parser = GeminiCommandParser(self.gemini_api_key, self.firebase_config)
            print("✅ Gemini AI model loaded with real-time state sync")
            
            # Set up command queue manager
            if self.connected:
                self.queue_manager = CommandQueueManager(self.firebase_config)
            
            # HTML monitor completely disabled - using Firebase only
            print("📄 HTML monitor disabled - using Firebase for all state updates")
            self.html_monitor = None
            
            return True
            
        except Exception as e:
            print(f"❌ Initialization error: {e}")
            return False
    
    def show_welcome_message(self):
        """Display welcome message and instructions"""
        print("\n" + "="*80)
        print("🎯 SEISMIC NAVIGATION AI ASSISTANT")
        print("="*80)
        print("Welcome! I'm your AI assistant for seismic navigation in Tornado software.")
        print("I understand natural language commands and can help you navigate seismic data.")
        print()
        print("🔥 Firebase Status:", "✅ Connected" if self.connected else "❌ Disconnected")
        print("🧠 AI Model: Gemini Pro (Google)")
        print("📄 HTML Monitor:", "✅ Active" if self.html_monitor else "❌ Inactive")
        print()
        print("💬 EXAMPLE COMMANDS:")
        print("  • 'move to crossline 165000, inline 115000, depth 4000'")
        print("  • 'move the slice a bit to the left'")
        print("  • 'zoom in and increase the gain'")
        print("  • 'show only seismic data, hide everything else'")
        print("  • 'what's my current position?'")
        print("  • 'help' - show all available commands")
        print()
        print("🤖 I can ask follow-up questions if your command is unclear!")
        print("📝 Type 'quit' to exit, 'help' for commands, 'status' for current state")
        print("="*80)
        print()
    
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """Process user input through Gemini parser"""
        try:
            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'bye']:
                return {"type": "quit", "message": "Goodbye!"}
            
            # Check for clarification response
            if self.parser.pending_clarification:
                result = self.parser.handle_clarification_response(user_input)
            else:
                result = self.parser.parse_command(user_input)
            
            # Update conversation history
            self.parser.update_conversation_history(user_input, result)
            
            return result
            
        except Exception as e:
            return {
                "type": "error",
                "message": f"Error processing command: {str(e)}",
                "suggestion": "Please try rephrasing your command or type 'help' for assistance."
            }
    
    def send_command_to_firebase(self, command: Dict[str, Any]) -> bool:
        """Send validated command to Firebase queue"""
        if not self.connected:
            print("⚠️  Firebase not connected - command not sent to Tornado")
            return False
        
        try:
            command_data = {
                "method": command["method"],
                "params": command["params"]
            }
            
            command_id = self.queue_manager.add_command(command_data)
            if command_id:
                print(f"📤 Command sent to Tornado (ID: {command_id[:8]}...)")
                return True
            else:
                print("❌ Failed to send command to Firebase queue")
                return False
                
        except Exception as e:
            print(f"❌ Error sending command: {e}")
            return False
    
    def display_result(self, result: Dict[str, Any], user_input: str):
        """Display result of command processing"""
        result_type = result.get("type", "unknown")
        
        if result_type == "command":
            # Valid command - show feedback and send to Firebase
            feedback = result.get("feedback", "Command processed")
            print(f"🤖 {feedback}")
            
            if self.connected:
                success = self.send_command_to_firebase(result)
                if success:
                    print("✅ Command queued for execution in Tornado")
                else:
                    print("❌ Failed to queue command")
            else:
                print("⚠️  Command parsed but not sent (Firebase disconnected)")
                print(f"📋 JSON-RPC: {json.dumps({'method': result['method'], 'params': result['params']}, indent=2)}")
        
        elif result_type == "clarification":
            # Need clarification - ask follow-up question
            question = result.get("question", "Could you clarify?")
            options = result.get("options", [])
            
            print(f"🤔 {question}")
            if options:
                print("   Options:")
                for i, option in enumerate(options, 1):
                    print(f"   {i}. {option}")
            print("💭 Please clarify your request:")
        
        elif result_type == "info":
            # Information request - show info
            message = result.get("message", "Information not available")
            print(f"ℹ️  {message}")
        
        elif result_type == "multi_command":
            # Multi-command sequence - execute each command
            commands = result.get("commands", [])
            feedback = result.get("feedback", "Executing multiple commands")
            print(f"🤖 {feedback}")
            
            if self.connected:
                success_count = 0
                for i, command in enumerate(commands, 1):
                    print(f"   {i}. Executing: {command['method']}")
                    success = self.send_command_to_firebase(command)
                    if success:
                        success_count += 1
                        print(f"      ✅ Command {i} queued")
                    else:
                        print(f"      ❌ Command {i} failed")
                
                print(f"📊 {success_count}/{len(commands)} commands queued successfully")
            else:
                print("⚠️  Commands parsed but not sent (Firebase disconnected)")
                for i, command in enumerate(commands, 1):
                    print(f"   {i}. {command['method']}: {command['params']}")
        
        elif result_type == "error":
            # Error - show error and suggestion
            message = result.get("message", "Unknown error")
            suggestion = result.get("suggestion", "Please try again")
            print(f"❌ {message}")
            print(f"💡 {suggestion}")
        
        elif result_type == "quit":
            print(f"👋 {result.get('message', 'Goodbye!')}")
            return False
        
        return True
    
    def on_html_change(self, change_message: str):
        """Handle HTML bookmark changes"""
        print(f"\n🔄 Tornado Updated:")
        print(f"   {change_message.replace(chr(10), chr(10) + '   ')}")
        print()
        
        # Show prompt again
        if self.parser and self.parser.pending_clarification:
            print("🤔 clarify> ", end="", flush=True)
        else:
            print("🎯 seismic> ", end="", flush=True)
    
    def start_status_monitor(self):
        """Start background thread to monitor Firebase connection and HTML changes"""
        def monitor():
            while self.running:
                try:
                    time.sleep(30)  # Check every 30 seconds
                    
                    # Could add connection health checks here
                    # For now, just keep the thread alive
                    
                except Exception as e:
                    if self.running:
                        print(f"\n⚠️  Status monitor error: {e}")
                    break
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        
        # Start HTML monitoring
        if self.html_monitor:
            self.html_monitor.start_monitoring(self.on_html_change, interval=0.5)
    
    def run(self):
        """Main terminal loop"""
        if not self.parser:
            print("❌ Failed to initialize - exiting")
            return
        
        self.running = True
        self.show_welcome_message()
        self.start_status_monitor()
        
        try:
            while self.running:
                try:
                    # Show appropriate prompt
                    if self.parser.pending_clarification:
                        prompt = "🤔 clarify> "
                    else:
                        prompt = "🎯 seismic> "
                    
                    # Get user input
                    user_input = input(prompt).strip()
                    
                    if not user_input:
                        continue
                    
                    # Process input
                    print("🧠 Processing...")
                    result = self.process_user_input(user_input)
                    
                    # Display result
                    continue_running = self.display_result(result, user_input)
                    if not continue_running:
                        break
                    
                    print()  # Add spacing between interactions
                    
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except EOFError:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"\n❌ Unexpected error: {e}")
                    print("💡 Please try again or type 'quit' to exit")
                    
        finally:
            self.running = False
            if self.html_monitor:
                self.html_monitor.stop_monitoring()
            print("🔄 Shutting down AI assistant...")


def main():
    """Main function to run the NLP chat terminal"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='NLP Chat Terminal for Seismic Navigation')
    parser.add_argument('--enable-html-monitor', action='store_true', 
                       help='Enable HTML bookmark monitoring (for testing on same machine)')
    args = parser.parse_args()
    
    # Load environment configuration
    env_config = EnvConfig()
    
    # Get API key from environment
    api_key = env_config.gemini_api_key
    if not api_key:
        print("❌ Cannot start without valid Gemini API key")
        print("💡 Please update your .env file with:")
        print("   GEMINI_API_KEY=your_actual_gemini_api_key")
        return
    
    try:
        print("🚀 Starting Seismic Navigation AI Assistant...")
        if args.enable_html_monitor:
            print("🧪 HTML monitoring enabled (testing mode)")
        
        # Create and run terminal
        terminal = NLPChatTerminal(api_key, enable_html_monitor=args.enable_html_monitor)
        terminal.run()
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()