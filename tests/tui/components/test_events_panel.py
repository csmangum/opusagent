import pytest
from textual.app import App
from tui.components import EventsPanel

class SingleWidgetApp(App):
    def compose(self):
        self.panel = EventsPanel()
        yield self.panel

@pytest.mark.asyncio
async def test_events_panel_add_event():
    app = SingleWidgetApp()
    async with app.run_test() as pilot:
        panel = app.panel
        assert isinstance(panel, EventsPanel)
        panel.add_event("session.initiate", status="success", details="Test event")
        assert panel.event_count == 1
        assert panel.events_log is not None 