import pytest
from textual.app import App
from textual.widgets import Static
from tui.components import StatusBar

class SingleWidgetApp(App):
    def compose(self):
        self.bar = StatusBar()
        yield self.bar

@pytest.mark.asyncio
async def test_status_bar_update_methods():
    app = SingleWidgetApp()
    async with app.run_test() as pilot:
        bar = app.bar
        assert isinstance(bar, StatusBar)
        bar.update_connection_status("Connected")
        bar.update_audio_status("Playing")
        bar.update_latency(123.4)
        bar.increment_message_count()
        bar.increment_error_count()
        status_widget = bar.query_one("#status-text", Static)
        status_text = str(status_widget.renderable)
        assert "Connected" in status_text
        assert "Playing" in status_text
        assert "123" in status_text
        assert "Messages: 1" in status_text
        assert "Errors: 1" in status_text 