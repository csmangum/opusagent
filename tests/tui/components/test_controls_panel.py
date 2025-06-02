import pytest
from textual.app import App
from textual.widgets import Button
from tui.components import ControlsPanel

class SingleWidgetApp(App):
    def compose(self):
        self.panel = ControlsPanel()
        yield self.panel

@pytest.mark.asyncio
async def test_controls_panel_button_states():
    app = SingleWidgetApp()
    async with app.run_test() as pilot:
        panel = app.panel
        assert isinstance(panel, ControlsPanel)
        panel.set_connection_state(True)
        start_btn = panel.query_one("#start-call-btn", Button)
        assert not start_btn.disabled
        panel.start_call()
        assert panel.call_active
        assert start_btn.disabled 