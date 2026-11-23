import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, writeFileSync, rmSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { listArtifacts, main, missingReports } from '../testhub-missing-reports.mjs';

const config = (name, coverage = true) => ({
  'sub-project': name, 'test-artifact-name': `test-results-${name}`,
  'coverage-tool': coverage ? 'coverage.py' : '',
  'coverage-artifact-name': coverage ? `xmlcov-${name}` : '',
});
const artifactsFor = configs => configs.flatMap(item => [item['test-artifact-name'], item['coverage-artifact-name']])
  .filter(Boolean).map(name => ({ name, expired: false }));
const ensure = resolve('.github/scripts/ensure-reports.sh');

test('the cancelled platform job is recovered without dropping later sub-projects', () => {
  const registry = JSON.parse(readFileSync('.github/testhub-projects.json', 'utf8'));
  const configs = ['python', 'node', 'rust'].flatMap(kind => (registry[kind] ?? []).map(item =>
    config(item.name, item.coverage_tool !== '')));
  const artifacts = artifactsFor(configs).filter(item => !item.name.endsWith('-platform-backend'));
  const original = JSON.stringify(configs);
  assert.deepEqual(missingReports(configs, artifacts), [{ ...config('platform-backend'),
    missing_test: true, missing_coverage: true }]);
  assert(configs.some(item => item['sub-project'] === 'platform-backend'));
  assert.equal(JSON.stringify(configs), original);
});

test('complete artifacts produce an empty recovery matrix', () => {
  const configs = [config('python'), config('no-coverage', false)];
  assert.deepEqual(missingReports(configs, artifactsFor(configs)), []);
});

test('missing coverage alone never replaces actual test results', () => {
  const item = config('python');
  assert.deepEqual(missingReports([item], [{ name: item['test-artifact-name'] }]), [
    { ...item, missing_test: false, missing_coverage: true },
  ]);
});

test('expired artifacts need recovery and duplicate/path-traversing names are rejected', () => {
  const item = config('python');
  assert.equal(missingReports([item], artifactsFor([item]).map(value => ({ ...value, expired: true }))).length, 1);
  assert.throws(() => missingReports([item, item], []), /duplicate/);
  assert.throws(() => missingReports([{ ...item, 'test-artifact-name': '../private' }], []), /Invalid/);
});

test('GitHub Enterprise pagination reads all pages with the run token', async () => {
  const calls = [];
  const result = await listArtifacts({ apiUrl: 'https://github.example/api/v3/',
    repository: 'org/repo', runId: '123', token: 'test-token' }, async (url, options) => {
    calls.push(url);
    assert.equal(options.headers.Authorization, 'Bearer test-token');
    assert.equal(options.redirect, 'error');
    return { ok: true, json: async () => ({ total_count: 2,
      artifacts: [{ name: calls.length === 1 ? 'test-results-python' : 'xmlcov-python' }] }) };
  });
  assert.equal(result.length, 2);
  assert.match(calls[0], /api\/v3\/repos\/org\/repo\/actions\/runs\/123\/artifacts\?per_page=100&page=1$/);
  assert.match(calls[1], /page=2$/);
});

test('API errors or incomplete listings fail instead of silently dropping projects', async () => {
  const env = { apiUrl: 'https://github.example/api/v3', repository: 'org/repo', runId: '123', token: 'test-token' };
  await assert.rejects(listArtifacts(env, async () => ({ ok: false, status: 403 })), /HTTP 403/);
  await assert.rejects(listArtifacts(env, async () => ({ ok: true,
    json: async () => ({ total_count: 1, artifacts: [] }) })), /ended before/);
});

test('a hung test process is bounded and produces failure/zero-coverage placeholders', () => {
  const root = mkdtempSync(join(tmpdir(), 'testhub-timeout-'));
  try {
    const timed = spawnSync('timeout', ['--signal=TERM', '--kill-after=.1s', '.1s',
      'sh', '-c', "trap '' TERM; sleep 30"], { timeout: 3000 });
    assert.notEqual(timed.status, 0);
    const generated = spawnSync('sh', [ensure, 'platform-backend', join(root, 'tests'), join(root, 'coverage')]);
    assert.equal(generated.status, 0);
    const report = readFileSync(join(root, 'tests/result.xml'), 'utf8');
    assert.match(report, /failures="1"/);
    assert.match(report, /<failure message="no test report was produced">/);
    assert.match(readFileSync(join(root, 'coverage/coverage.xml'), 'utf8'), /line-rate="0"/);
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test('existing reports are preserved by recovery', () => {
  const root = mkdtempSync(join(tmpdir(), 'testhub-preserve-'));
  try {
    mkdirSync(join(root, 'tests')); mkdirSync(join(root, 'coverage'));
    const result = '<testsuite tests="2" failures="0"/>';
    const coverage = '<coverage line-rate="0.8"/>';
    writeFileSync(join(root, 'tests/result.xml'), result);
    writeFileSync(join(root, 'coverage/coverage.xml'), coverage);
    assert.equal(spawnSync('sh', [ensure, 'python', join(root, 'tests'), join(root, 'coverage')]).status, 0);
    assert.equal(readFileSync(join(root, 'tests/result.xml'), 'utf8'), result);
    assert.equal(readFileSync(join(root, 'coverage/coverage.xml'), 'utf8'), coverage);
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test('the recovery matrix is written as one valid GitHub output', async () => {
  const root = mkdtempSync(join(tmpdir(), 'testhub-output-'));
  try {
    const request = async () => ({ ok: true, json: async () => ({ total_count: 0, artifacts: [] }) });
    const warnings = [];
    await main({ TESTHUB_CONFIGS: JSON.stringify([config('platform-backend')]),
      GITHUB_API_URL: 'https://github.example/api/v3', GITHUB_REPOSITORY: 'org/repo',
      GITHUB_RUN_ID: '123', GITHUB_TOKEN: 'test-token',
      GITHUB_OUTPUT: join(root, 'output'), GITHUB_STEP_SUMMARY: join(root, 'summary') },
      request, value => warnings.push(value));
    const output = readFileSync(join(root, 'output'), 'utf8');
    assert.equal(output.trim().split('\n').length, 1);
    assert.deepEqual(JSON.parse(output.slice('missing='.length)), [
      { ...config('platform-backend'), missing_test: true, missing_coverage: true },
    ]);
    assert.match(readFileSync(join(root, 'summary'), 'utf8'), /Recovering failure placeholders/);
    assert.match(warnings[0], /::warning::Missing reports for platform-backend/);
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test('selective coverage recovery creates no dummy test result', () => {
  const root = mkdtempSync(join(tmpdir(), 'testhub-coverage-only-'));
  try {
    const result = spawnSync('sh', [ensure, 'python', '', join(root, 'coverage')]);
    assert.equal(result.status, 0);
    assert.doesNotMatch(result.stdout.toString(), /no test report/);
    assert.match(readFileSync(join(root, 'coverage/coverage.xml'), 'utf8'), /line-rate="0"/);
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test('recovered failure details identify the producer run and escape XML', () => {
  const root = mkdtempSync(join(tmpdir(), 'testhub-details-'));
  try {
    const result = spawnSync('sh', [ensure, 'python', join(root, 'tests'), ''], {
      env: { ...process.env, REPORT_FAILURE_CONTEXT: 'Producer <cancelled> & timed out: https://github.example/actions/runs/123' },
    });
    assert.equal(result.status, 0);
    assert.match(readFileSync(join(root, 'tests/result.xml'), 'utf8'), /Producer <cancelled> &amp; timed out: https:\/\/github.example\/actions\/runs\/123/);
  } finally { rmSync(root, { recursive: true, force: true }); }
});
