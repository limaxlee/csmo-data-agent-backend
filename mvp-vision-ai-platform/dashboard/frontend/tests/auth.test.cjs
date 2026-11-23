const assert = require("node:assert/strict")
const { test } = require("node:test")
const { readFileSync } = require("node:fs")
const path = require("node:path")
const Module = require("node:module")
const ts = require("typescript")

// Exercise the same TS client as the app without adding a second test framework.
const filename = path.resolve(__dirname, "../lib/auth.ts")
function loadAuthModule() {
  const loaded = new Module(filename, module)
  loaded.filename = filename
  loaded.paths = module.paths
  loaded._compile(ts.transpileModule(readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, filename)
  return loaded
}
const loaded = loadAuthModule()
const { verifyAdminSession, authNavigationUrl } = loaded.exports

const config = { authBaseUrl: "http://localhost:3020/auth", userApiUrl: "http://localhost:8003/api/v1" }
const session = { authenticated: true, roles: [], expiresAt: 1 }
const token = () => ({ accessToken: "signed-service-token", tokenType: "Bearer", expiresAt: Math.floor(Date.now() / 1000) + 3600 })
const admin = { id: "canonical-user-id", system_role: "admin", is_active: true, full_name: "Admin" }
const response = (body, status = 200) => new Response(JSON.stringify(body), { status })

function fixture(responses) {
  const calls = []
  const controller = new AbortController()
  const fetcher = async (url, options) => {
    calls.push({ url, ...options })
    assert.ok(responses.length, `Unexpected request to ${url}`)
    const next = responses.shift()
    if (next instanceof Error) throw next
    return typeof next === "function" ? next() : next
  }
  return {
    calls, controller,
    verify: () => verifyAdminSession(config, controller.signal, fetcher),
  }
}

test("callback preserves the requested path/query/hash across local ports", () => {
  const current = "http://localhost:3391/dashboard?tab=project#history"
  const login = new URL(authNavigationUrl(config, "login", current))
  assert.equal(login.origin, "http://localhost:3020")
  assert.equal(login.pathname, "/auth/login")
  assert.equal(login.searchParams.get("callbackUrl"), current)
  const sameOrigin = { ...config, authBaseUrl: "" }
  const logout = new URL(authNavigationUrl(sameOrigin, "logout", current), current)
  assert.equal(logout.searchParams.get("redirect"), "/dashboard?tab=project#history")
})

test("activation API defaults to the Activation dashboard route and supports an explicit backend URL", () => {
  const previousAuthBase = process.env.NEXT_PUBLIC_AUTH_BASE_URL
  const previousActivationBase = process.env.NEXT_PUBLIC_ACTIVATION_API_URL
  try {
    process.env.NEXT_PUBLIC_AUTH_BASE_URL = "http://localhost:3020/auth/"
    delete process.env.NEXT_PUBLIC_ACTIVATION_API_URL
    assert.equal(loadAuthModule().exports.serviceApiBaseUrls.activation, "/activation/dashboard")

    process.env.NEXT_PUBLIC_ACTIVATION_API_URL = "https://auth.example.test/custom/activation/dashboard/"
    assert.equal(loadAuthModule().exports.serviceApiBaseUrls.activation, "https://auth.example.test/custom/activation/dashboard")
  } finally {
    if (previousAuthBase === undefined) delete process.env.NEXT_PUBLIC_AUTH_BASE_URL
    else process.env.NEXT_PUBLIC_AUTH_BASE_URL = previousAuthBase
    if (previousActivationBase === undefined) delete process.env.NEXT_PUBLIC_ACTIVATION_API_URL
    else process.env.NEXT_PUBLIC_ACTIVATION_API_URL = previousActivationBase
  }
})

test("only the authoritative active admin profile grants access; service expiry wins", async () => {
  const issued = token()
  const f = fixture([response(session), response(issued), response(admin)])
  const identity = await f.verify()
  assert.equal(identity.user.id, "canonical-user-id")
  assert.equal(identity.expiresAt, issued.expiresAt)
  assert.deepEqual(f.calls.map(c => c.url), [
    "http://localhost:3020/auth/session", "http://localhost:3020/auth/token", "http://localhost:8003/api/v1/users/me",
  ])
  assert.equal(f.calls[0].credentials, "include")
  assert.equal(f.calls[1].credentials, "include")
  assert.equal(f.calls[2].credentials, "omit")
  assert.equal(f.calls[2].headers.Authorization, "Bearer signed-service-token")
  assert.ok(f.calls.every(c => c.signal instanceof AbortSignal && c.cache === "no-store"))
})

test("missing central session stops before token/profile requests", async () => {
  const f = fixture([response({ authenticated: false })])
  await assert.rejects(f.verify(), { kind: "unauthenticated" })
  assert.equal(f.calls.length, 1)
})

test("central admin claims do not grant access to a non-admin profile", async () => {
  const f = fixture([response({ ...session, roles: ["admin"] }), response(token()), response({ ...admin, system_role: "member" })])
  await assert.rejects(f.verify(), { kind: "forbidden" })
})

test("development and production both require an active admin profile", async () => {
  const original = process.env.NODE_ENV
  try {
    for (const env of ["development", "production"]) {
      process.env.NODE_ENV = env
      const { verifyAdminSession: verify } = loadAuthModule().exports
      for (const profile of [admin, { ...admin, system_role: "member" }, { ...admin, is_active: false }]) {
        const responses = [response(session), response(token()), response(profile)]
        const result = verify(config, new AbortController().signal, async () => responses.shift())
        if (profile.system_role === "admin" && profile.is_active) {
          assert.equal((await result).user.id, admin.id)
        } else {
          await assert.rejects(result, { kind: "forbidden" })
        }
      }
    }
  } finally {
    if (original === undefined) delete process.env.NODE_ENV
    else process.env.NODE_ENV = original
  }
})

test("inactive users and HTTP 403 are forbidden without token retry", async () => {
  for (const result of [response({ ...admin, is_active: false }), response({}, 403)]) {
    const f = fixture([response(session), response(token()), result])
    await assert.rejects(f.verify(), { kind: "forbidden" })
    assert.equal(f.calls.length, 3)
  }
})

test("malformed/expired token responses never reach user-service", async () => {
  for (const issued of [{}, { ...token(), expiresAt: 1 }, { ...token(), expiresAt: "bad" }, { ...token(), accessToken: "" }]) {
    const f = fixture([response(session), response(issued)])
    await assert.rejects(f.verify(), { kind: "unavailable" })
    assert.equal(f.calls.length, 2)
  }
})

test("invalid session and incomplete/malformed admin profiles fail closed", async () => {
  for (const body of [{}, { authenticated: "true" }, null]) {
    const f = fixture([response(body)])
    await assert.rejects(f.verify(), { kind: "unavailable" })
  }
  for (const body of [{ ...admin, id: "" }, { system_role: "admin" }, { ...admin, is_active: "true" }, null]) {
    const f = fixture([response(session), response(token()), response(body)])
    await assert.rejects(f.verify(), { kind: "unavailable" })
  }
})

test("central token 401 requires login", async () => {
  const f = fixture([response(session), response({}, 401)])
  await assert.rejects(f.verify(), { kind: "unauthenticated" })
})

test("profile GET 401 retries once with a newly acquired token", async () => {
  const f = fixture([response(session), response(token()), response({}, 401), response({ ...token(), accessToken: "fresh" }), response(admin)])
  await f.verify()
  assert.equal(f.calls.length, 5)
  assert.equal(f.calls[4].headers.Authorization, "Bearer fresh")
})

test("persistent profile 401 is an error instead of an automatic login loop", async () => {
  const f = fixture([response(session), response(token()), response({}, 401), response(token()), response({}, 401)])
  await assert.rejects(f.verify(), { kind: "unavailable" })
  assert.equal(f.calls.length, 5)
})

test("auth and user-service failures stay distinguishable from missing login", async () => {
  for (const result of [new TypeError("Failed to fetch"), response({}, 503), new Response("not json")]) {
    const f = fixture([result])
    await assert.rejects(f.verify(), { kind: "unavailable" })
  }
  const f = fixture([response(session), response(token()), response({}, 500)])
  await assert.rejects(f.verify(), { kind: "unavailable" })
})

test("an aborted/late profile cannot restore admin access", async () => {
  const f = fixture([response(session), response(token()), () => {
    f.controller.abort()
    return response(admin)
  }])
  await assert.rejects(f.verify(), { name: "AbortError" })
})

test("an auth timeout is unavailable, not a redirect to login", async () => {
  const fetcher = (_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true })
  })
  await assert.rejects(verifyAdminSession(config, new AbortController().signal, fetcher, 5), { kind: "unavailable" })
})

function loadProvider() {
  const providerFile = path.resolve(__dirname, "../components/DashboardAuthProvider.tsx")
  const provider = new Module(providerFile, module)
  provider.filename = providerFile
  provider.paths = module.paths
  provider.require = (id) => id === "../lib/auth" ? loaded.exports : require(id)
  provider._compile(ts.transpileModule(readFileSync(providerFile, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText, providerFile)
  return provider.exports
}

test("initial server render contains no protected Dashboard content", () => {
  const React = require("react")
  const { renderToString } = require("react-dom/server")
  const markup = renderToString(React.createElement(loadProvider().default, null,
    React.createElement("div", null, "PROTECTED-CONTENT")))
  assert.ok(markup.includes("로그인 및 관리자 권한을 확인하고 있습니다."))
  assert.ok(!markup.includes("PROTECTED-CONTENT"))
})

test("Dashboard header has a local logo, ordered cross-app links, and the active Admin marker", () => {
  const React = require("react")
  const { renderToString } = require("react-dom/server")
  const file = path.resolve(__dirname, "../components/SiteHeader.tsx")
  const header = new Module(file, module)
  header.filename = file
  header.paths = module.paths
  header._compile(ts.transpileModule(readFileSync(file, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText, file)
  const html = renderToString(React.createElement(header.exports.default, {
    homeHref: "https://site.test/",
    logoSrc: "/dashboard/dice_symbolNlettermark.png",
    activeHref: "/dashboard",
    navLinks: [
      { label: "Defect", href: "https://site.test/defect" },
      { label: "Trainer", href: "http://localhost:3030/platform" },
      { label: "Admin", href: "/dashboard" },
      { label: "Docs", href: "https://site.test/docs/ko/guide/overview" },
    ],
  }))
  assert.ok(html.includes('href="https://site.test/"'))
  assert.ok(html.includes('src="/dashboard/dice_symbolNlettermark.png"'))
  assert.ok(html.includes('<a href="https://site.test/defect">Defect</a><span class="dice-nav-divider" aria-hidden="true"></span><a href="http://localhost:3030/platform">Trainer</a>'))
  assert.ok(html.includes('href="/dashboard" aria-current="page">Admin</a>'))
  assert.ok(html.includes('href="https://site.test/docs/ko/guide/overview"'))
  assert.ok(html.includes("로그인"))
})

test("navigation defaults to deployed paths and supports local service URL overrides", () => {
  const keys = ["NEXT_PUBLIC_SITE_URL", "NEXT_PUBLIC_BASE_PATH", "NEXT_PUBLIC_LABELER_URL", "NEXT_PUBLIC_TRAINER_URL", "NEXT_PUBLIC_RUNNER_URL", "NEXT_PUBLIC_DEFECT_URL", "NEXT_PUBLIC_DOCS_URL", "NEXT_PUBLIC_DOWNLOAD_URL", "NEXT_PUBLIC_ACTIVATION_URL"]
  const before = Object.fromEntries(keys.map(key => [key, process.env[key]]))
  function navigation() {
    const file = path.resolve(__dirname, "../lib/navigation.ts")
    const loaded = new Module(file, module)
    loaded._compile(ts.transpileModule(readFileSync(file, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS },
    }).outputText, file)
    return loaded.exports.navigation
  }
  try {
    keys.forEach(key => delete process.env[key])
    assert.deepEqual(navigation().links.map(link => link.href), ["/defect", "/labeler", "/platform", "/runner", "/docs/ko/guide/overview", "/downloads", "/activation", "/dashboard"])
    assert.deepEqual(navigation().links.map(link => link.label), ["Defect", "Labeler", "Trainer", "Runner", "Docs", "Download", "Activation", "Admin"])
    process.env.NEXT_PUBLIC_SITE_URL = "https://site.test/"
    process.env.NEXT_PUBLIC_TRAINER_URL = "http://localhost:3030/platform"
    assert.equal(navigation().home, "https://site.test/")
    assert.equal(navigation().links[0].href, "https://site.test/defect")
    assert.equal(navigation().links[2].href, "http://localhost:3030/platform")
    assert.equal(navigation().links[4].href, "https://site.test/docs/ko/guide/overview")
  } finally {
    keys.forEach(key => { if (before[key] === undefined) delete process.env[key]; else process.env[key] = before[key] })
  }
})

function loadApiClient() {
  const filename = path.resolve(__dirname, "../lib/api/client.ts")
  const loaded = new Module(filename, module)
  loaded.filename = filename
  loaded.paths = module.paths
  loaded._compile(ts.transpileModule(readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, filename)
  return loaded.exports
}

test("service client retries a GET once with the refreshed admin token", async () => {
  const { APIClient } = loadApiClient()
  const calls = []
  const originalFetch = global.fetch
  global.fetch = async (_url, options) => {
    calls.push(options.headers.get("Authorization"))
    return calls.length === 1
      ? response({ detail: "expired" }, 401)
      : response({ ok: true })
  }
  try {
    const client = new APIClient("/platform/api/v1", () => ({
      accessToken: "old-token",
      signal: new AbortController().signal,
      refresh: async () => "new-token",
    }))
    assert.deepEqual(await client.get("/dashboard/users/active-count"), { ok: true })
    assert.deepEqual(calls, ["Bearer old-token", "Bearer new-token"])
  } finally {
    global.fetch = originalFetch
  }
})

test("service client never automatically replays a mutation after 401", async () => {
  const { APIClient, ApiError } = loadApiClient()
  const originalFetch = global.fetch
  let calls = 0
  let refreshes = 0
  global.fetch = async () => { calls += 1; return response({ detail: "expired" }, 401) }
  try {
    const client = new APIClient("/user/api/v1", () => ({
      accessToken: "old-token",
      signal: new AbortController().signal,
      refresh: async () => { refreshes += 1; return "new-token" },
    }))
    await assert.rejects(client.patch("/dashboard/users/confirm", { id: "user-1" }), error => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.kind, "unauthenticated")
      return true
    })
    assert.equal(calls, 1)
    assert.equal(refreshes, 0)
  } finally {
    global.fetch = originalFetch
  }
})

test("service client preserves HTTP error categories and handles 204", async () => {
  const { APIClient, ApiError } = loadApiClient()
  const originalFetch = global.fetch
  const outcomes = [response({ detail: "forbidden" }, 403), new Response(null, { status: 204 })]
  global.fetch = async () => outcomes.shift()
  try {
    const client = new APIClient("/labeler/api/v1", () => ({
      accessToken: "admin-token",
      signal: new AbortController().signal,
      refresh: async () => null,
    }))
    await assert.rejects(client.get("/datasets"), error => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.kind, "forbidden")
      assert.equal(error.status, 403)
      return true
    })
    assert.equal(await client.delete("/datasets/1"), null)
  } finally {
    global.fetch = originalFetch
  }
})

test("service client cancels in-flight requests with the protected-session signal", async () => {
  const { APIClient } = loadApiClient()
  const session = new AbortController()
  const originalFetch = global.fetch
  global.fetch = async (_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true })
  })
  try {
    const client = new APIClient("/platform/api/v1", () => ({
      accessToken: "admin-token",
      signal: session.signal,
      refresh: async () => null,
    }))
    const pending = client.get("/dashboard/projects/count")
    session.abort()
    await assert.rejects(pending, { name: "AbortError" })
  } finally {
    global.fetch = originalFetch
  }
})

