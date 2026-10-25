import unittest
from pathlib import Path

from gdhq.settings import ROOT


class WorkflowSafetyTests(unittest.TestCase):
    def test_unconfigured_templates_are_inert_and_preserved(self):
        for name in ('ada', 'agent-container', 'agent-self-hosted', 'alibabacloud', 'aws', 'copilot-setup-steps', 'label'):
            workflow = (ROOT/'.github/workflows'/f'{name}.yml').read_text()
            self.assertIn('workflow_dispatch:', workflow)
            self.assertIn('if: ${{ false }}', workflow)
            self.assertIn('permissions: {}', workflow)
            for trigger in ('push:', 'pull_request:', 'pull_request_target:', 'schedule:'):
                self.assertNotIn(trigger, workflow)
            self.assertTrue((ROOT/'docs/quarantined-workflows'/f'{name}.yml.txt').is_file())

    def test_windows_deployment_keeps_owner_confirmation_and_nonpersisted_credentials(self):
        workflow = (ROOT/'.github/workflows/deploy-windows.yml').read_text()
        self.assertIn("inputs.confirmation == 'DEPLOY_LOCAL'", workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn('persist-credentials: false', workflow)
        self.assertIn('shell: cmd', workflow)

    def test_model_audit_can_run_before_local_deployment(self):
        workflow = (ROOT/'.github/workflows/deploy-windows.yml').read_text()
        self.assertLess(workflow.index('scripts/audit_models.py'), workflow.index('Back up and install local code'))


if __name__ == '__main__':
    unittest.main()
