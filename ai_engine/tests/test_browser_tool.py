import unittest


class BrowserStateTests(unittest.TestCase):

    def test_stores_current_url(self):
        from ai_engine.app.browser import BrowserState

        state = BrowserState(
            current_url="https://example.com",
            title="Example",
        )

        self.assertEqual(
            state.current_url,
            "https://example.com",
        )

    def test_stores_page_title(self):
        from ai_engine.app.browser import BrowserState

        state = BrowserState(
            current_url="https://example.com",
            title="Example",
        )

        self.assertEqual(
            state.title,
            "Example",
        )


class BrowserToolTests(unittest.TestCase):

    def test_opens_page(self):
        from ai_engine.app.browser import BrowserTool

        browser = BrowserTool()

        state = browser.open_page(
            "https://example.com",
        )

        self.assertEqual(
            state.current_url,
            "https://example.com",
        )

    def test_navigates_to_new_page(self):
        from ai_engine.app.browser import BrowserTool

        browser = BrowserTool()

        browser.open_page(
            "https://example.com",
        )

        state = browser.navigate(
            "https://example.com/about",
        )

        self.assertEqual(
            state.current_url,
            "https://example.com/about",
        )

    def test_extracts_information(self):
        from ai_engine.app.browser import BrowserTool

        browser = BrowserTool()

        result = browser.extract_information(
            "page heading",
        )

        self.assertEqual(
            result,
            "page heading",
        )

    def test_interacts_with_target(self):
        from ai_engine.app.browser import BrowserTool

        browser = BrowserTool()

        result = browser.interact(
            target="submit_button",
            action="click",
        )

        self.assertTrue(result)

    def test_returns_current_state(self):
        from ai_engine.app.browser import BrowserTool

        browser = BrowserTool()

        browser.open_page(
            "https://example.com",
        )

        state = browser.get_state()

        self.assertEqual(
            state.current_url,
            "https://example.com",
        )


if __name__ == "__main__":
    unittest.main()
