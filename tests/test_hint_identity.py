"""L'identità della conversazione segue l'id di sessione del client, non solo la catena di hash.
   python3 -m unittest -v tests.test_hint_identity"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ctxproxy.core import chain  # noqa: E402
from tests.test_proxy import Base, TOOLS, history  # noqa: E402


def req(msgs):
    return {"model": "m", "messages": msgs, "tools": TOOLS}


COMPACT = [{"role": "system", "content": "Sei un agente di programmazione. " * 20},
           {"role": "user", "content": "<checkpoint> riassunto dei primi passi, poi «continua»"},
           {"role": "user", "content": "continua"}]


class HintIdentity(Base):
    """conv_of: la conv su cui il client viene riconosciuto adesso."""

    def conv_of(self, msgs):
        return self.proxy.store.find_conv(chain(msgs, TOOLS))[0]

    def test_compaction_keeps_the_same_conversation(self):
        """Il client compatta (la storia diventa un riassunto): la conv resta la stessa, così recall,
        segmenti e pin della parte compattata restano raggiungibili."""
        msgs = history(3)
        self.assertEqual(self.proxy.chat(req(msgs), "ses_A")[0], 200)
        first = self.conv_of(msgs)
        self.assertTrue(first.startswith("c-"))          # nata dall'hint
        self.assertEqual(self.proxy.chat(req(COMPACT), "ses_A")[0], 200)
        self.assertEqual(first, self.conv_of(COMPACT))
        self.assertEqual(self.proxy.store.find_hint("ses_A"), first)

    def test_two_sessions_with_the_same_system_prompt_stay_separate(self):
        """Due sessioni nuove condividono h_0 (system + strumenti): non vanno unite."""
        a = [{"role": "system", "content": "Sei un agente di programmazione. " * 20},
             {"role": "user", "content": "progetto A"}]
        b = [{"role": "system", "content": "Sei un agente di programmazione. " * 20},
             {"role": "user", "content": "progetto B"}]
        self.assertEqual(self.proxy.chat(req(a), "ses_A")[0], 200)
        self.assertEqual(self.proxy.chat(req(b), "ses_B")[0], 200)
        self.assertNotEqual(self.conv_of(a), self.conv_of(b))

    def test_new_hint_on_a_known_chain_joins_that_conversation(self):
        """Fork / sessione riaperta: hint mai visto, ma la storia è quella già nota -> stessa conv."""
        msgs = history(3)
        self.assertEqual(self.proxy.chat(req(msgs), "ses_A")[0], 200)
        first = self.conv_of(msgs)
        self.assertEqual(self.proxy.chat(req(msgs), "ses_B")[0], 200)
        self.assertEqual(first, self.conv_of(msgs))
        self.assertEqual(self.proxy.store.find_hint("ses_B"), first)

    def test_without_hint_the_chain_decides_as_before(self):
        """Senza hint il comportamento è quello di sempre: si riconosce dalla catena, h_0 compreso."""
        msgs = history(3)
        self.assertEqual(self.proxy.chat(req(msgs), None)[0], 200)
        first = self.conv_of(msgs)
        self.assertFalse(first.startswith("c-"))         # id generato qui, come prima
        self.assertEqual(self.proxy.chat(req(COMPACT), None)[0], 200)
        self.assertEqual(first, self.conv_of(COMPACT))   # riconosciuto da h_0, come prima
        self.assertIsNone(self.proxy.store.find_hint("ses_A"))


class HintFromHeaders(unittest.TestCase):
    """conv_hint legge gli header dei client (case-insensitive) e poi prompt_cache_key."""

    def setUp(self):
        from ctxproxy.core import conv_hint
        self.conv_hint = conv_hint

    def test_order(self):
        self.assertEqual(self.conv_hint({"X-Session-Id": "ses_1"}, {"prompt_cache_key": "pk"}), "ses_1")
        self.assertEqual(self.conv_hint({"x-session-id": " ses_2 "}, None), "ses_2")      # minuscolo, come opencode
        self.assertEqual(self.conv_hint({"x-session-affinity": "ses_3"}, None), "ses_3")
        self.assertEqual(self.conv_hint({}, {"prompt_cache_key": "pk"}), "pk")
        self.assertEqual(self.conv_hint({"X-Strata-Conversation": "x", "X-Session-Id": "s"}, None), "x")

    def test_absent(self):
        self.assertIsNone(self.conv_hint({"X-Session-Id": "   "}, {"prompt_cache_key": ""}))
        self.assertIsNone(self.conv_hint({}, None))
        self.assertIsNone(self.conv_hint(None, {"prompt_cache_key": 42}))


if __name__ == "__main__":
    unittest.main()
