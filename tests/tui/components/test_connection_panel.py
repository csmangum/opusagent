import pytest
from textual.app import App
from textual.widgets import Button
from tui.components import ConnectionPanel

class SingleWidgetApp(App):
    def compose(self):
        self.panel = ConnectionPanel()
        yield self.panel

@pytest.mark.asyncio
async def test_connection_panel_mount_and_button_press():
    app = SingleWidgetApp()
    async with app.run_test() as pilot:
        panel = app.panel
        assert isinstance(panel, ConnectionPanel)
        await pilot.click("#connect-btn")
        connect_btn = panel.query_one("#connect-btn", Button)
        assert not connect_btn.disabled 