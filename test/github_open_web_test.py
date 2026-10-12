"""Regression tests for repository and branch selection in `ghow`."""

from importlib.util import module_from_spec, spec_from_file_location
from os import chdir, getcwd
from pathlib import Path
from subprocess import check_call
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import call, patch

from click.testing import CliRunner


ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location('github_open_web', ROOT / 'github/github-open-web.py')
module = module_from_spec(spec)
spec.loader.exec_module(module)


class GithubOpenWebTest(TestCase):
    def setUp(self) -> None:
        scratch = ROOT / 'tmp'
        scratch.mkdir(exist_ok=True)
        directory = TemporaryDirectory(prefix='ghow-test-', dir=scratch)
        self.addCleanup(directory.cleanup)
        self.addCleanup(chdir, getcwd())
        chdir(directory.name)
        self.environment = patch.dict('os.environ', {'GIT_CONFIG_GLOBAL': '/dev/null'})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.git('init', '--quiet', '--initial-branch=new-since-filter')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '--quiet', '--allow-empty', '-m', 'Initial')
        self.git('remote', 'add', 'h', 'git@github.com:HackJerseyCity/jc-taxes.git')

    def git(self, *args: str) -> None:
        check_call(['git', *args])

    def configure_upstream(
        self,
        remote: str,
        branch: str = 'new-since-filter',
    ) -> None:
        self.git('config', 'branch.new-since-filter.remote', remote)
        self.git('config', 'branch.new-since-filter.merge', f'refs/heads/{branch}')

    def assert_open(
        self,
        args: list[str],
        expected: list[str],
    ) -> None:
        with patch.object(module, 'get_default_branch', return_value='main'), patch.object(module, 'check_call') as launch:
            result = CliRunner().invoke(module.github_open_web, args)
        self.assertEqual(result.exit_code, 0, result.exception)
        self.assertEqual(launch.call_args_list, [call(expected)])

    def test_url_upstream_without_remote_tracking_ref(self) -> None:
        self.configure_upstream('git@github.com:alfonsoar/jc-taxes.git')
        self.assert_open([], ['gh', 'repo', 'view', 'alfonsoar/jc-taxes', '--web', '-b', 'new-since-filter'])

    def test_named_upstream_with_different_branch_name(self) -> None:
        self.git('remote', 'add', 'a', 'https://github.com/alfonsoar/jc-taxes.git')
        self.configure_upstream('a', 'feature/filter')
        self.assert_open([], ['gh', 'repo', 'view', 'alfonsoar/jc-taxes', '--web', '-b', 'feature/filter'])

    def test_explicit_branch_uses_its_upstream(self) -> None:
        self.configure_upstream('https://github.com/alfonsoar/jc-taxes.git', 'feature/filter')
        self.assert_open(['-b', 'new-since-filter'], ['gh', 'repo', 'view', 'alfonsoar/jc-taxes', '--web', '-b', 'feature/filter'])

    def test_explicit_remote_overrides_upstream(self) -> None:
        self.configure_upstream('git@github.com:alfonsoar/jc-taxes.git')
        self.assert_open(['h'], ['gh', 'repo', 'view', 'HackJerseyCity/jc-taxes', '--web', '-b', 'new-since-filter'])

    def test_explicit_repo_overrides_matching_remote(self) -> None:
        self.git('update-ref', 'refs/remotes/h/new-since-filter', 'HEAD')
        self.configure_upstream('git@github.com:alfonsoar/jc-taxes.git')
        self.assert_open(['-R', 'other/jc-taxes'], ['gh', 'repo', 'view', 'other/jc-taxes', '--web', '-b', 'new-since-filter'])

    def test_default_does_not_select_pr_fork(self) -> None:
        self.configure_upstream('git@github.com:alfonsoar/jc-taxes.git')
        self.assert_open(['-d'], ['gh', 'repo', 'view', '--web'])

    def test_unconfigured_branch_keeps_remote_ref_fallback(self) -> None:
        self.git('update-ref', 'refs/remotes/h/new-since-filter', 'HEAD')
        self.assert_open([], ['gh', 'repo', 'view', 'HackJerseyCity/jc-taxes', '--web', '-b', 'new-since-filter'])


if __name__ == '__main__':
    main()
