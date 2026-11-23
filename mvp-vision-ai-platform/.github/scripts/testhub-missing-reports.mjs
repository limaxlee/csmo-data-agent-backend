/** Recover missing producer artifacts without dropping a TestHub sub-project. */
import { appendFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

export function missingReports(configs, artifacts) {
  const available = new Set(artifacts.filter(artifact => !artifact.expired).map(artifact => artifact.name));
  const missing = [];
  const names = new Set();
  for (const config of configs) {
    for (const key of ['test-artifact-name', 'coverage-artifact-name']) {
      const name = config[key];
      if (!name && key === 'coverage-artifact-name' && !config['coverage-tool']) continue;
      if (typeof name !== 'string' || !/^[A-Za-z0-9_-]+$/.test(name) || names.has(name)) {
        throw new Error(`Invalid or duplicate ${key}`);
      }
      names.add(name);
    }
    const missing_test = !available.has(config['test-artifact-name']);
    const missing_coverage = Boolean(config['coverage-tool']) && !available.has(config['coverage-artifact-name']);
    if (missing_test || missing_coverage) missing.push({ ...config, missing_test, missing_coverage });
  }
  return missing;
}

export async function listArtifacts({ apiUrl, repository, runId, token }, request = fetch) {
  if (!apiUrl || !/^[^/]+\/[^/]+$/.test(repository) || !/^\d+$/.test(runId) || !token) {
    throw new Error('Missing GitHub artifact API configuration');
  }
  const repo = repository.split('/').map(encodeURIComponent).join('/');
  const artifacts = [];
  for (let page = 1; ; page++) {
    const response = await request(
      `${apiUrl.replace(/\/$/, '')}/repos/${repo}/actions/runs/${runId}/artifacts?per_page=100&page=${page}`,
      { headers: { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json' },
        redirect: 'error', signal: AbortSignal.timeout(30_000) },
    );
    if (!response.ok) throw new Error(`Artifact listing failed: HTTP ${response.status}`);
    const data = await response.json();
    if (!Array.isArray(data.artifacts) || !Number.isInteger(data.total_count)) {
      throw new Error('Invalid artifact listing response');
    }
    artifacts.push(...data.artifacts);
    if (artifacts.length >= data.total_count) return artifacts;
    if (!data.artifacts.length) throw new Error('Artifact listing ended before total_count');
  }
}

export async function main(env = process.env, request = fetch, log = console.log) {
  if (!env.GITHUB_OUTPUT) throw new Error('GITHUB_OUTPUT is required');
  const configs = JSON.parse(env.TESTHUB_CONFIGS);
  if (!Array.isArray(configs)) throw new Error('TESTHUB_CONFIGS must be an array');
  const artifacts = await listArtifacts({ apiUrl: env.GITHUB_API_URL, repository: env.GITHUB_REPOSITORY,
    runId: env.GITHUB_RUN_ID, token: env.GITHUB_TOKEN }, request);
  const missing = missingReports(configs, artifacts);
  for (const report of missing) {
    const message = `Missing reports for ${report['sub-project']}: test=${report.missing_test}, coverage=${report.missing_coverage}. Recovering failure placeholders.`;
    log(`::warning::${message}`);
    if (env.GITHUB_STEP_SUMMARY) appendFileSync(env.GITHUB_STEP_SUMMARY, `${message}\n\n`);
  }
  appendFileSync(env.GITHUB_OUTPUT, `missing=${JSON.stringify(missing)}\n`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}

