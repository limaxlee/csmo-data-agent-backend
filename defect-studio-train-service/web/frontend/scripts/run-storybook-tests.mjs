import http from 'node:http';
import net from 'node:net';
import { spawn, spawnSync } from 'node:child_process';

const host = '127.0.0.1';
const timeoutMs = Number(process.env.STORYBOOK_WAIT_TIMEOUT_MS || 60_000);
const testRetries = Number(process.env.STORYBOOK_TEST_RETRIES || 1);
const isWindows = process.platform === 'win32';
const packageManager = process.env.npm_execpath?.includes('pnpm') ? 'pnpm' : 'npm';

let shuttingDown = false;

function runPackageManager(args) {
  const options = {
    cwd: process.cwd(),
    env: { ...process.env, BROWSER: 'none' },
    stdio: 'inherit',
  };

  if (isWindows) {
    return spawn([packageManager, ...args].join(' '), { ...options, shell: true });
  }

  return spawn(packageManager, args, {
    ...options,
  });
}

function runStorybook(port) {
  if (packageManager === 'pnpm') {
    return runPackageManager(['exec', 'storybook', 'dev', '-p', port, '--ci', '--host', host]);
  }

  return runPackageManager(['exec', 'storybook', '--', 'dev', '-p', port, '--ci', '--host', host]);
}

function runStorybookTests(url) {
  if (packageManager === 'pnpm') {
    return runPackageManager(['run', 'test-storybook', '--url', url]);
  }

  return runPackageManager(['run', 'test-storybook', '--', '--url', url]);
}

function canListen(port) {
  return new Promise((resolve) => {
    const server = net.createServer();

    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close(() => resolve(true));
    });
    server.listen(port);
  });
}

async function findAvailablePort() {
  const preferredPort = Number(process.env.STORYBOOK_TEST_PORT || 6006);

  for (let port = preferredPort; port < preferredPort + 50; port += 1) {
    if (await canListen(port)) {
      return String(port);
    }
  }

  throw new Error(`No available Storybook test port from ${preferredPort} to ${preferredPort + 49}`);
}

function requestOk(targetUrl) {
  return new Promise((resolve) => {
    const request = http.get(targetUrl, (response) => {
      response.resume();
      resolve(Boolean(response.statusCode && response.statusCode < 500));
    });

    request.on('error', () => resolve(false));
    request.setTimeout(1000, () => {
      request.destroy();
      resolve(false);
    });
  });
}

async function waitForServer(url) {
  const start = Date.now();

  while (Date.now() - start < timeoutMs) {
    if (await requestOk(url)) {
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  throw new Error(`Storybook did not start at ${url} within ${timeoutMs}ms`);
}

function waitForExit(child) {
  return new Promise((resolve) => {
    child.on('exit', (code) => resolve(code ?? 1));
  });
}

function stopProcessTree(child) {
  if (!child.pid || child.exitCode !== null) return;

  if (isWindows) {
    spawnSync('taskkill', ['/pid', String(child.pid), '/t', '/f'], { stdio: 'ignore' });
    return;
  }

  child.kill('SIGTERM');
}

const port = await findAvailablePort();
const url = `http://${host}:${port}`;
const storybook = runStorybook(port);

storybook.on('exit', (code) => {
  if (!shuttingDown && code !== 0) {
    console.error(`Storybook exited before tests completed with code ${code}`);
  }
});

try {
  await waitForServer(url);
  for (let attempt = 0; attempt <= testRetries; attempt += 1) {
    const tests = runStorybookTests(url);
    const code = await waitForExit(tests);

    if (code === 0) {
      process.exitCode = 0;
      break;
    }

    process.exitCode = code;
    if (attempt < testRetries) {
      console.error(`Storybook tests failed with code ${code}; retrying (${attempt + 1}/${testRetries})...`);
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  shuttingDown = true;
  stopProcessTree(storybook);
}
