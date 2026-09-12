# pylint: disable=protected-access

import unittest
from unittest.mock import patch

from pdf_craft.llm import LLM
from pdf_craft.transformer import XMLTranslator


class _Context:
    def __init__(self) -> None:
        self.messages = None

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def request(self, input):
        self.messages = input
        return "সংশোধিত লেখা"


class _Runtime:
    def __init__(self) -> None:
        self.last_context = _Context()

    def context(self, **_kwargs):
        return self.last_context


class TestProofreadingPrompt(unittest.TestCase):
    def test_proofreading_template_forbids_translation_and_guessing(self):
        llm = LLM("key", "http://localhost:11434/v1", "qwen", "o200k_base")
        rendered = llm.template("proofread").render(
            target_language="Bangla (Bengali)", user_prompt="Keep archaic names."
        )
        self.assertIn("Bangla (Bengali)", rendered)
        self.assertIn("Do not translate", rendered)
        self.assertIn("leave it unchanged rather than guessing", rendered)
        self.assertIn("Keep archaic names.", rendered)

    def test_xml_translator_uses_selected_proofreading_template(self):
        llm = LLM("key", "http://localhost:11434/v1", "qwen", "o200k_base")
        runtime = _Runtime()
        with patch(
            "pdf_craft.transformer.xml_translator.xml_translator.translator.runtime_for",
            return_value=runtime,
        ):
            translator = XMLTranslator(
                translation_llm=llm,
                fill_llm=llm,
                target_language="Bangla (Bengali)",
                user_prompt=None,
                ignore_translated_error=False,
                max_retries=1,
                max_fill_displaying_errors=1,
                max_group_score=100,
                prompt_template="proofread",
            )

        self.assertEqual(translator._translate_text("ভূল লেখা"), "সংশোধিত লেখা")
        messages = runtime.last_context.messages
        self.assertIsNotNone(messages)
        assert messages is not None
        system_message = messages[0].message
        self.assertIn("meticulous proofreader", system_message)
        self.assertIn("Do not translate", system_message)


if __name__ == "__main__":
    unittest.main()
