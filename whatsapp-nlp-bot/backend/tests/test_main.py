import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

import main


class AnalyzeSentimentTests(unittest.TestCase):
    def test_falls_back_to_keyword_sentiment_when_textblob_fails(self):
        with patch("main.TextBlob", side_effect=Exception("boom")):
            self.assertEqual(main.analyze_sentiment("I love this"), "positive")
            self.assertEqual(main.analyze_sentiment("This is terrible"), "negative")
            self.assertEqual(main.analyze_sentiment("Please help"), "neutral")


class ScamDetectionTests(unittest.TestCase):
    def test_detects_shortened_link_as_scam(self):
        text = "Check this out: https://onelink.me/qcrE/mk037k2j"
        result = main.detect_scam(text)
        self.assertTrue(result.get("is_scam"))
        self.assertIn("shortened_link", result.get("reasons"))

    def test_detects_suspicious_language(self):
        text = "Urgent! Verify your account now or it will be suspended"
        result = main.detect_scam(text)
        self.assertTrue(result.get("is_scam"))
        self.assertIn("suspicious_language", result.get("reasons"))


class ClassificationTests(unittest.TestCase):
    def test_classifies_phishing(self):
        text = "Your account is suspended. Verify your account here: http://bit.ly/abc123 and enter your password"
        cls = main.classify_message(text)
        self.assertEqual(cls.get("category"), "phishing")

    def test_classifies_fake_news(self):
        text = "BREAKING: Celebrity just confirmed they're pregnant!!! This is unbelievable and viral"
        cls = main.classify_message(text)
        self.assertEqual(cls.get("category"), "fake_news")


if __name__ == "__main__":
    unittest.main()
