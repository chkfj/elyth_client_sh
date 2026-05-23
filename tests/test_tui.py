import unittest
from client.tui.app import ElythApp
from client.tui.widgets.post_card import PostCard
from textual.widgets import TabbedContent, Button, ContentSwitcher
from textual.containers import ScrollableContainer
from textual.markup import MarkupError


class TestElythTUI(unittest.IsolatedAsyncioTestCase):
    async def test_app_mounts_with_tabs(self):
        """Verify app mounts with all expected tabs."""
        app = ElythApp(mock_mode=True)
        async with app.run_test() as pilot:
            await pilot.pause()
            
            tabs_view = app.query_one("#tabs-view", TabbedContent)
            self.assertIsNotNone(tabs_view)

    async def test_help_text_markup_is_valid(self):
        """Verify help text has valid markup without errors."""
        app = ElythApp(mock_mode=True)
        help_text = app._get_help_text()
        try:
            from textual.content import Content
            Content.from_markup(help_text)
        except MarkupError as e:
            self.fail(f"Help text has invalid markup: {e}")

    async def test_timeline_shows_post_cards(self):
        """Verify timeline container shows PostCard widgets."""
        app = ElythApp(mock_mode=True)
        async with app.run_test() as pilot:
            await pilot.pause()
            
            timeline = app.query_one("#timeline-container", ScrollableContainer)
            post_cards = list(timeline.query(PostCard))
            self.assertGreater(len(post_cards), 0, "Timeline should have at least one post card")

    async def test_post_card_reply_button_exists(self):
        """Test Reply button exists on post card."""
        app = ElythApp(mock_mode=True)
        async with app.run_test() as pilot:
            await pilot.pause()
            
            timeline = app.query_one("#timeline-container", ScrollableContainer)
            post_card = timeline.query(PostCard).first()
            self.assertIsNotNone(post_card)
            
            reply_btn = post_card.query_one("#reply-btn", Button)
            self.assertIsNotNone(reply_btn)

    async def test_post_card_thread_button_switches_to_thread_view(self):
        """Test clicking View Thread button switches to thread view."""
        app = ElythApp(mock_mode=True)
        async with app.run_test() as pilot:
            await pilot.pause()
            
            timeline = app.query_one("#timeline-container", ScrollableContainer)
            post_card = timeline.query(PostCard).first()
            
            thread_btn = post_card.query_one("#thread-btn", Button)
            thread_btn.press()
            await pilot.pause()
            
            switcher = app.query_one("#main-switcher", ContentSwitcher)
            self.assertEqual(switcher.current, "thread-view-container")

    async def test_escape_from_thread_view_returns_to_timeline(self):
        """Test Esc key returns from thread view to timeline."""
        app = ElythApp(mock_mode=True)
        async with app.run_test() as pilot:
            await pilot.pause()
            
            timeline = app.query_one("#timeline-container", ScrollableContainer)
            post_card = timeline.query(PostCard).first()
            
            thread_btn = post_card.query_one("#thread-btn", Button)
            thread_btn.press()
            await pilot.pause()
            
            switcher = app.query_one("#main-switcher", ContentSwitcher)
            self.assertEqual(switcher.current, "thread-view-container")
            
            await pilot.press("escape")
            await pilot.pause()
            
            self.assertEqual(switcher.current, "tabs-view")

    async def test_post_card_like_button_exists(self):
        """Test Like button exists on post card."""
        app = ElythApp(mock_mode=True)
        async with app.run_test() as pilot:
            await pilot.pause()
            
            timeline = app.query_one("#timeline-container", ScrollableContainer)
            post_card = timeline.query(PostCard).first()
            
            like_btn = post_card.query_one("#like-btn", Button)
            self.assertIsNotNone(like_btn)

if __name__ == "__main__":
    unittest.main()