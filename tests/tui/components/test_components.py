import pytest
from textual.app import App
from textual.widgets import Button, Static, Input
from tui.components import (
    ConnectionPanel, AudioPanel, EventsPanel, TranscriptPanel, ControlsPanel, StatusBar
)

# Helper app for mounting a single widget
class SingleWidgetApp(App):
    def __init__(self, widget_cls, **kwargs):
        super().__init__()
        self.widget_cls = widget_cls
        self.widget_kwargs = kwargs
        self.widget = None

    def compose(self):
        self.widget = self.widget_cls(**self.widget_kwargs)
        yield self.widget

@pytest.mark.asyncio
async def test_connection_panel_mount_and_button_press():
    app = SingleWidgetApp(ConnectionPanel)
    async with app.run_test() as pilot:
        # Check widget is present
        panel = app.widget
        assert isinstance(panel, ConnectionPanel)
        # Simulate pressing the connect button
        await pilot.click("#connect-btn")
        # The button should be present
        connect_btn = panel.query_one("#connect-btn", Button)
        assert connect_btn is not None

@pytest.mark.asyncio
async def test_events_panel_add_event():
    app = SingleWidgetApp(EventsPanel)
    async with app.run_test() as pilot:
        panel = app.widget
        assert isinstance(panel, EventsPanel)
        # Add an event and check log
        panel.add_event("session.initiate", status="success", details="Test event")
        assert panel.event_count == 1
        assert panel.events_log is not None

@pytest.mark.asyncio
async def test_transcript_panel_add_user_and_bot_message():
    app = SingleWidgetApp(TranscriptPanel)
    async with app.run_test() as pilot:
        panel = app.widget
        assert isinstance(panel, TranscriptPanel)
        panel.add_user_message("Hello user!")
        panel.add_bot_message("Hello bot!")
        assert panel.transcript_count == 2
        assert panel.transcript_log is not None

@pytest.mark.asyncio
async def test_controls_panel_button_states():
    app = SingleWidgetApp(ControlsPanel)
    async with app.run_test() as pilot:
        panel = app.widget
        assert isinstance(panel, ControlsPanel)
        # Simulate connection state change
        panel.set_connection_state(True)
        start_btn = panel.query_one("#start-call-btn", Button)
        assert not start_btn.disabled
        # Simulate starting a call
        panel.start_call()
        assert panel.call_active
        assert start_btn.disabled

@pytest.mark.asyncio
async def test_status_bar_update_methods():
    app = SingleWidgetApp(StatusBar)
    async with app.run_test() as pilot:
        bar = app.widget
        assert isinstance(bar, StatusBar)
        bar.update_connection_status("Connected")
        bar.update_audio_status("Playing")
        bar.update_latency(123.4)
        bar.increment_message_count()
        bar.increment_error_count()
        # Check that the status bar text updates
        status_widget = bar.query_one("#status-text", Static)
        status_text = str(status_widget.renderable)
        assert "Connected" in status_text
        assert "Playing" in status_text
        assert "123" in status_text
        assert "Messages: 1" in status_text
        assert "Errors: 1" in status_text 