import pytest
from textual.app import App
from tui.components import TranscriptPanel

class SingleWidgetApp(App):
    def compose(self):
        self.panel = TranscriptPanel()
        yield self.panel

@pytest.mark.asyncio
async def test_transcript_panel_add_user_and_bot_message():
    app = SingleWidgetApp()
    async with app.run_test() as pilot:
        panel = app.panel
        assert isinstance(panel, TranscriptPanel)
        panel.add_user_message("Hello user!")
        panel.add_bot_message("Hello bot!")
        assert panel.transcript_count == 2
        assert panel.transcript_log is not None 