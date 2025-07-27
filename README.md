# iRacing MCP Server

An MCP (Model Context Protocol) server for accessing iRacing telemetry data and game functionality.

## Overview

This project provides real-time telemetry data, leaderboard information, camera control, pit commands, replay functionality, and more from iRacing through the MCP protocol. It enables AI assistants and other applications to easily access iRacing data.

## Key Features

### 📊 Telemetry Data
- Retrieve real-time telemetry values
- Get list of available telemetry variables

### 🏁 Race Information
- Get leaderboard (competitive positions only)
- Access driver information, session information, weekend information, and split time information
- Monitor current flags and engine warnings

### 📹 Camera Control
- Get available camera groups
- Switch cameras (by car number, position, group specification)
- Check current camera status

### 🔧 Pit Operations
- Check pit service status
- Execute pit commands (refueling, tire changes, repairs, etc.)
- Manage safe pit operations

### 🎬 Replay Features
- Search and navigate replays
- Move between sessions, laps, and frames
- Jump to incident markers

## Requirements

- Python 3.13 or higher
- iRacing (must be running)
- uv

## Usage

### 1. Configure mcp.json
```json
{
    "mcpServers": {
        "iracing-mcp-server": {
            "command": "uvx",
            "args":["iracing-mcp-server"]
        }
    }
}
```

## Available Tools

### Telemetry Related
- `get_telemetry_names()` - Get available telemetry variables
- `get_telemetry_values(names)` - Get specified telemetry values

### Race Information
- `get_leaderboard()` - Get leaderboard
- `get_driver_info()` - Get driver information
- `get_session_info()` - Get session information
- `get_qualify_results_info()` - Get qualification results information
- `get_weekend_info()` - Get weekend information
- `get_split_time_info()` - Get split time information
- `get_radio_info()` - Get radio infomation
- `get_current_flags()` - Get current flags
- `get_current_engine_warnings()` - Get engine warnings

### Camera Control
- `get_camera_info()` - Get camera information
- `get_current_camera_status()` - Get current camera status
- `cam_switch(group_number, car_number_raw, position)` - Switch camera

### Pit Operations
- `get_current_pit_service_status()` - Get current pit service status
- `pit_command(commands_and_values)` - Execute pit command

### Replay Features
- `replay_search(search_commands)` - Search and navigate replay

## Development

### Dependencies
- `mcp[cli]>=1.12.2` - MCP protocol implementation
- `pyirsdk>=1.3.5` - iRacing SDK Python bindings

### Project Structure
```
iracing-mcp-server/
├── src/iracing_mcp_server/
│   ├── __init__.py          # Main entry point
│   ├── server.py            # MCP server implementation
│   ├── leaderboard.py       # Leaderboard processing
│   └── prompt.py            # Prompt templates
├── pyproject.toml           # Project configuration
└── README.md               # This file
```

## License

This project is released under the MIT License.

## Acknowledgments

- [pyirsdk](https://github.com/kutu/pyirsdk) - Python bindings for iRacing SDK
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
