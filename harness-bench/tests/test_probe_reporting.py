import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from probes import p3_asr

class ProbeReportingTests(unittest.TestCase):
    def test_empty_asr_corpus_is_blocked_and_never_passed(self):
        root=Path(tempfile.mkdtemp(prefix="cx1-asr-report-"))
        with patch.object(p3_asr, "CORPUS", root), patch.object(p3_asr, "build_bias_lists", return_value=([],[])):
            result=p3_asr.run(None,None,True)
        self.assertEqual(result["status"],"blocked")
        self.assertIsNone(result["avg_wer"])
        self.assertEqual(result["files"],0)
