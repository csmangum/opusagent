import pytest
from textual.app import App
from textual.widgets import Button
from tui.components import AudioPanel

class SingleWidgetApp(App):
    def compose(self):
        self.panel = AudioPanel()
        yield self.panel

@pytest.mark.asyncio
async def test_audio_panel_volume_buttons():
    app = SingleWidgetApp()
    async with app.run_test() as pilot:
        panel = app.panel
        assert isinstance(panel, AudioPanel)
        up_btn = panel.query_one("#volume-up-btn", Button)
        down_btn = panel.query_one("#volume-down-btn", Button)
        old_volume = panel.volume
        # Click volume up
        await pilot.click("#volume-up-btn")
        assert panel.volume > old_volume
        # Click volume down
        await pilot.click("#volume-down-btn")
        assert panel.volume <= old_volume + 0.1 