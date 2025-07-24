# Stage 3: Distributed Command Execution System

## Overview

Stage 3 implements a distributed command execution system where:
1. **AI Laptop Terminal** - User types JSON-RPC commands
2. **Firebase Queue** - Commands are queued for processing
3. **Tornado Listener** - Processes commands and calls bookmark engine methods

## Architecture

```
AI Laptop Terminal (json_rpc_terminal.py)
    ↓ JSON-RPC Commands
Firebase Queue (firebase_config.py)
    ↓ Command Processing
Tornado Listener (tornado_listener.py)
    ↓ Method Calls
Bookmark Engine V2 (bookmark_engine_v2.py)
    ↓ HTML Generation
Tornado Display Update
```

## Available JSON-RPC Commands

All commands from `bookmark_gui_tkinter_tornadoless.py` are available:

### Position/Navigation
- `update_position(x, y, z)` - Update crossline/inline/depth position
- `update_orientation(rot1, rot2, rot3)` - Update view rotation angles
- `update_scale(scale_x, scale_y)` - Update zoom/scale
- `update_shift(shift_x, shift_y, shift_z)` - Update view shift

### Visibility Controls
- `update_visibility(seismic, attribute, horizon, well)` - Toggle data visibility
- `update_slice_visibility(x_slice, y_slice, z_slice)` - Toggle slice visibility

### Display Adjustments
- `update_gain(gain_value)` - Adjust gain/amplitude range
- `update_colormap(colormap_index)` - Change colormap
- `update_color_scale(times_value)` - Adjust color scale

### Quick Actions
- `increase_gain()`, `decrease_gain()` - Adjust gain by preset amounts
- `rotate_left()`, `rotate_right()` - Rotate view
- `zoom_in()`, `zoom_out()`, `zoom_reset()` - Zoom controls

### State Management
- `undo_action()`, `redo_action()` - Undo/redo functionality
- `reset_parameters()` - Reset all to defaults
- `reload_template()` - Reload bookmark template

## Setup Instructions

### 1. Firebase Configuration

Create `firebase_credentials.json` with your Firebase service account credentials:

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

### 2. Initialize Firebase Database

```bash
cd src/firebase
python firebase_config.py
```

This creates the required database structure:
- `/command_queues/{user_id}/commands/{command_id}`
- `/user_sessions/{user_id}`
- `/system_status/tornado_listener`

### 3. Test the System

```bash
cd src/tests
python test_distributed_flow.py
```

This runs comprehensive tests:
- ✅ Basic command flow
- ✅ Command queue ordering
- ✅ Error handling
- ✅ Multi-user isolation
- ✅ Bookmark modification integration

## Usage

### 1. Start Tornado Listener (in Tornado environment)

```bash
# Inside Tornado
Tornadoi -script /path/to/src/tornado/tornado_listener.py
```

The listener will:
- Initialize seismic data and default view
- Connect to Firebase queue
- Process commands continuously
- Never terminate (critical for Tornado)

### 2. Use JSON-RPC Terminal (on AI laptop)

```bash
cd src/terminal
python json_rpc_terminal.py
```

Example commands:
```json
{"method": "update_position", "params": {"x": 160000, "y": 112000, "z": 3500}}
{"method": "zoom_in", "params": {}}
{"method": "rotate_left", "params": {}}
{"method": "update_gain", "params": {"gain_value": 1.5}}
{"method": "update_visibility", "params": {"seismic": true, "attribute": false, "horizon": false, "well": true}}
```

### 3. Monitor Status

In the terminal, use:
- `help` - Show available commands
- `status` - Show system and queue status
- `quit` - Exit terminal

## Key Features

### Command Validation
- JSON structure validation
- Parameter type checking
- Method existence verification
- Required parameter validation

### Error Handling
- Firebase connection errors
- Invalid command handling
- Tornado API error recovery
- Automatic retry mechanisms

### Multi-User Support
- Isolated command queues per user
- Session management
- Concurrent user handling

### Real-Time Processing
- 2-second polling interval
- Status updates and heartbeats
- Command execution feedback

### Logging
- Comprehensive logging in Tornado listener
- Error tracking and debugging
- Performance monitoring

## File Structure

```
src/
├── firebase/
│   └── firebase_config.py      # Firebase setup and queue management
├── terminal/
│   └── json_rpc_terminal.py    # AI laptop terminal interface
├── tornado/
│   └── tornado_listener.py     # Tornado command processor
└── tests/
    └── test_distributed_flow.py # Comprehensive testing
```

## Next Steps

After Stage 3 completion:
1. **Stage 4**: Add LLM command interpretation
2. **Stage 5**: Connect natural language to Firebase queue
3. **Stage 6**: Enhanced chat frontend
4. **Stage 7**: Speech recognition and advanced features

## Troubleshooting

### Firebase Connection Issues
- Check `firebase_credentials.json` exists and is valid
- Verify Firebase project permissions
- Check network connectivity

### Tornado Listener Issues
- Ensure script never terminates
- Check bookmark engine initialization
- Verify seismic data loading

### Command Processing Issues
- Check JSON format in terminal
- Verify parameter names and types
- Monitor Firebase queue status

## Testing

The system includes comprehensive tests:
- Unit tests for individual components
- Integration tests for end-to-end flow
- Multi-user isolation testing
- Error handling validation
- Performance benchmarking

Run tests before deployment to ensure system reliability.