import unittest
import logging
from opusagent.config.logging_config import configure_logging

class TestLoggingConfig(unittest.TestCase):
    def test_configure_logging(self):
        # Test that the function returns a logger
        logger = configure_logging()
        self.assertIsInstance(logger, logging.Logger)
        
        # Test that the logger has the correct name
        self.assertEqual(logger.name, "opusagent")
        
        # Test that the logger has the correct level
        self.assertEqual(logger.level, logging.DEBUG)
        
        # Test that the logger has the correct handlers and format
        self.assertGreaterEqual(len(logger.handlers), 1)  # At least one handler (console)
        handler = logger.handlers[0]  # Check first handler (should be console handler)
        self.assertIsInstance(handler, logging.StreamHandler)
        formatter = handler.formatter
        self.assertIsNotNone(formatter, "Handler should have a formatter")
        assert formatter is not None  # Type assertion for linter
        self.assertEqual(formatter._fmt, "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

if __name__ == "__main__":
    unittest.main() 