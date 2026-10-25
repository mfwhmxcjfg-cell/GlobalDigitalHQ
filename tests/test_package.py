import os,sys,unittest,tempfile
from pathlib import Path
from gdhq.roles import ROLES
from gdhq.settings import ROOT
from gdhq.builder import BANNED
from gdhq.auditing import file_digests

class PackageTests(unittest.TestCase):
    def test_css_js_html(self):
        for x in ['index.html','style.css','app.js']:
            self.assertTrue((ROOT/'web'/x).is_file())
    def test_js_is_local(self):
        js=(ROOT/'web'/'app.js').read_text(encoding='utf-8')
        # Public endpoint strings are configuration examples; the UI only calls its own backend.
        self.assertIn("fetch(path,opts)",js)
        self.assertNotRegex(js,r'''fetch\(\s*["']https?://''')
        html=(ROOT/'web/index.html').read_text(encoding='utf-8')
        self.assertNotRegex(html,r'''<script[^>]+src=["']https?://''')
    def test_catalog(self):self.assertEqual(len(ROLES),40)
    def test_windows_scripts(self):
        for x in ['INSTALLER_WINDOWS.cmd','LANCER.cmd','VERIFIER.cmd','scripts/AUDIT_2H.cmd','scripts/INSTALLER_AUDIT_2H.cmd']:
            self.assertTrue((ROOT/x).is_file(),x)
    def test_manifest(self):
        manifest=ROOT/'MANIFEST.sha256'
        self.assertTrue(manifest.is_file())
        expected={name:digest for digest,name in (line.split('  ',1) for line in manifest.read_text(encoding='utf-8').splitlines() if '  ' in line)}
        self.assertEqual(expected,dict(file_digests()))
