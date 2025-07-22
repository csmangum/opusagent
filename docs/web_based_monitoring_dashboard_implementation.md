# Web-Based Monitoring Dashboard Implementation

The web-based monitoring dashboard provides real-time visibility into OpusAgent's operations, including session metrics, system health, active connections, and logs. It builds on existing stats endpoints and can be extended for comprehensive monitoring.

## Overview

The dashboard enables:
- **Real-Time Monitoring**: View active sessions, connection stats, and system health.
- **Log Viewing**: Browse and search application logs.
- **Metrics Visualization**: Charts for audio quality, latency, and session trends.
- **Alerts**: Notifications for errors or performance issues.
- **Administrative Controls**: Session management and configuration tweaks.

This enhances observability, complementing the existing TUI.

## Architecture

### Core Components

```
opusagent/
├── dashboard/
│   ├── __init__.py
│   ├── app.py                 # FastAPI app for dashboard
│   ├── templates/             # HTML templates (Jinja2)
│   │   └── index.html
│   ├── static/                # CSS/JS assets
│   ├── models.py              # Dashboard data models
│   ├── views.py               # View functions
│   └── utils.py               # Helper utilities
```

### Integration Points

- **FastAPI Endpoints**: Extend main.py with /dashboard routes.
- **Existing Stats**: Use /stats, /health, get_session_stats().
- **Websocket**: Real-time updates via WebSockets.
- **Storage**: Pull session data from Redis/Memory.

## Implementation

### Dashboard App

Extend FastAPI in main.py:

```python
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from opusagent.dashboard import views

app = FastAPI()
templates = Jinja2Templates(directory="opusagent/dashboard/templates")

@app.get("/dashboard")
def dashboard(request: Request):
    stats = get_websocket_manager().get_stats()
    sessions = session_manager.list_active_sessions()
    return templates.TemplateResponse("index.html", {"request": request, "stats": stats, "sessions": sessions})
```

### Real-Time Updates

Use WebSockets for live data:

```python
@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await websocket.accept()
    while True:
        stats = get_session_stats()
        await websocket.send_json(stats)
        await asyncio.sleep(5)
```

## Integration with OpusAgent

### Metrics Collection

Aggregate from existing sources:

```python
def get_dashboard_metrics():
    return {
        "sessions": session_manager.get_session_stats(),
        "websocket": websocket_manager.get_stats(),
        "audio_quality": audio_quality_monitor.get_quality_summary(),
    }
```

### Log Integration

Add endpoint to fetch logs:

```python
@app.get("/logs")
def get_logs():
    with open(LOG_FILE, 'r') as f:
        return {"logs": f.readlines()[-100:]}  # Last 100 lines
```

## Configuration

### Environment Variables

```bash
DASHBOARD_ENABLED=true
DASHBOARD_PORT=8001
DASHBOARD_REFRESH_INTERVAL=5  # seconds
DASHBOARD_LOG_LINES=500
```

### Configuration Class

```python
class DashboardConfig:
    enabled: bool = True
    port: int = 8001
    refresh_interval: int = 5
```

## Usage Examples

### Accessing Dashboard

Run server with `DASHBOARD_ENABLED=true`, visit http://localhost:8001/dashboard.

### Custom Views

Add charts using Chart.js in index.html.

## Security Considerations

- **Authentication**: Add JWT or basic auth.
- **Access Control**: Restrict to admin users.
- **Data Sensitivity**: Mask sensitive info in logs/sessions.

## Testing

### Unit Tests

Test metrics aggregation and endpoints.

### Integration Tests

Simulate sessions and verify dashboard updates.

## Performance Considerations

- **Scalability**: Use caching for metrics.
- **Optimization**: Limit real-time updates frequency.

## Future Enhancements

- **Charts/Graphs**: Add visualizations for trends.
- **Alerts**: Email/Slack notifications.
- **Historical Data**: Store and query past metrics.

## Dependencies

- fastapi
- jinja2
- htmx (for dynamic updates)

## Troubleshooting

- **No Data**: Check stats endpoints.
- **Connection Issues**: Verify WebSocket config.

## Conclusion

This dashboard provides essential monitoring, extensible for production needs.