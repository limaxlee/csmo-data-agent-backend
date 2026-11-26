# Adding "Data Agent" to the DICE top menu

Written 2026-11-26. This describes the change. No code was changed.

The repo is `mvp-vision-ai-platform`. All paths below start at its top folder.

## Contents

- [The short version](#the-short-version)
- [Where the menu is](#where-the-menu-is)
- [Two things to decide first](#two-things-to-decide-first)
- [The changes, file by file](#the-changes-file-by-file)
- [The two test files](#the-two-test-files)
- [Checking it before you push](#checking-it-before-you-push)
- [How the change reaches the website](#how-the-change-reaches-the-website)
- [What changes for people](#what-changes-for-people)
- [If you want Data Agent before Defect instead](#if-you-want-data-agent-before-defect-instead)
- [What I could not see](#what-i-could-not-see)
- [Checklist](#checklist)

---

## The short version

The menu is not one list. The same header was copied into three separate DICE programs, and
each keeps its own list of links. The main page is one of them.

- **Main page only:** two lines to add and one word to change, all in one file
  (`web-auth/components/LandingPage.tsx`), plus one test to update. This is changes 1 and 2
  and test A below.
- **The same menu on every page** (main page, Download, Activation, Docs, Admin dashboard):
  eight small changes in eight files, plus two test files. In total, one new line in each of
  six lists, and one changed word in each of four headers.

I recommend doing all of it in one go. The header looks identical on all those pages, and a
menu that gains and loses an entry as you move between pages looks like a mistake.

The result:

```
today:   Defect | Labeler  Trainer  Runner  Docs  Download  Activation
after:   Defect  Data Agent | Labeler  Trainer  Runner  Docs  Download  Activation
```

The `|` is a thin grey line that the header draws on purpose. It separates the products that
are not part of the DICE suite from the suite itself. Today it is drawn after Defect. With
Data Agent placed after Defect, the line has to move one step to the right, so that both
agents stand on the same side of it. That is the "one word to change".

---

## Where the menu is

| Program | Pages it serves | Image it is built into | Where its link list is | Where its header draws the line |
|---|---|---|---|---|
| `web-auth` | Main page `/` | `dice-web-auth` | `web-auth/components/LandingPage.tsx`, two lists (Korean and English) | Same file |
| `web-auth` | `/downloads`, `/activation` | `dice-web-auth` | `web-auth/app/downloads/page.tsx` and `web-auth/app/activation/page.tsx`, one list each | `web-auth/components/SiteHeader.tsx` |
| `docs-site` | `/docs/...` | `dice-docs` | `docs-site/app/[lang]/layout.tsx` | `docs-site/components/SiteHeader.tsx` |
| `dashboard/frontend` | `/dashboard` (admins only) | `dice-dashboard-frontend` | `dashboard/frontend/lib/navigation.ts` | `dashboard/frontend/components/SiteHeader.tsx` |

Two test files check the order of the menu and the place of the line. They fail until they
are updated:

| Test file | What it checks |
|---|---|
| `web-auth/app/lib/headerNavigation.test.ts` | The exact list of labels on the main page, and that the line stands right after Defect |
| `dashboard/frontend/tests/auth.test.cjs` | The exact list of links of the dashboard header, and that the line stands right after Defect |

The "Admin" entry at the end of the menu is not in any of these lists. The header adds it by
itself for admins. Nothing changes there.

---

## Two things to decide first

### 1. Before or after Defect

I recommend **after Defect**, and the rest of this document is written that way.

- Defect keeps the first place it has today. The existing test is even named "renders Defect
  first", so the first place was chosen on purpose by someone.
- The new entry stands next to Defect, on the same side of the grey line, which is what you
  asked for.

The price is the one-word change in each of the four header files, to move the line.
[Before Defect](#if-you-want-data-agent-before-defect-instead) needs no change to the line.
That section lists what differs.

### 2. The address of the link

Use `/data-agent`, without a slash at the end.

Both spellings open the data agent. With `/data-agent/` the data agent first sends the browser
on to `/data-agent`, which is one extra hop. Every other entry in the list is written without
a slash at the end too (`/defect`, `/labeler`).

The label is `Data Agent`, two words with a space. The headers use the label as the name they
compare with to place the line, so it has to be spelled exactly the same in all places.

---

## The changes, file by file

Line numbers are from the copy of the repo I have. Search for the quoted text if they do not
match.

### Change 1. Main page: the two link lists

File: `web-auth/components/LandingPage.tsx`

The file holds the texts of the main page twice, once under `ko:` (about line 197) and once
under `en:` (about line 355). Each has a `nav` block with a `links` list. Add one line to
**both**, right after the Defect line.

Before (the Korean list; the English one differs only in the Docs address):

```tsx
    nav: {
      links: [
        { label: 'Defect', href: '/defect' },
        { label: 'Labeler', href: '/labeler' },
        { label: 'Trainer', href: '/platform' },
```

After:

```tsx
    nav: {
      links: [
        { label: 'Defect', href: '/defect' },
        { label: 'Data Agent', href: '/data-agent' },
        { label: 'Labeler', href: '/labeler' },
        { label: 'Trainer', href: '/platform' },
```

The page shown at `/` uses the Korean list (`web-auth/app/page.tsx` passes `lang="ko"`). The
English list has to get the line too, because the test checks both.

### Change 2. Main page: move the grey line

Same file, `web-auth/components/LandingPage.tsx`, about line 605, inside `<nav className="dice-nav">`.

Before:

```tsx
              <a href={link.href}>{link.label}</a>
              {link.label === 'Defect' && index < list.length - 1 ? (
                <span className="dice-nav-divider" aria-hidden="true" />
              ) : null}
```

After:

```tsx
              <a href={link.href}>{link.label}</a>
              {link.label === 'Data Agent' && index < list.length - 1 ? (
                <span className="dice-nav-divider" aria-hidden="true" />
              ) : null}
```

Only the word in quotes changes. It means: draw the line after the entry called Data Agent.

**For the main page alone, changes 1 and 2 and [test A](#test-a-web-auth) are everything.**
The rest makes the other pages match.

### Change 3. Download page: the link list

File: `web-auth/app/downloads/page.tsx`, about line 10.

Before:

```tsx
const NAV_LINKS: SiteHeaderNavLink[] = [
  { label: "Defect", href: "/defect" },
  { label: "Labeler", href: "/labeler" },
```

After:

```tsx
const NAV_LINKS: SiteHeaderNavLink[] = [
  { label: "Defect", href: "/defect" },
  { label: "Data Agent", href: "/data-agent" },
  { label: "Labeler", href: "/labeler" },
```

### Change 4. Activation page: the link list

File: `web-auth/app/activation/page.tsx`, about line 8. The list looks exactly like the one in
change 3. Add the same line in the same place:

```tsx
  { label: "Data Agent", href: "/data-agent" },
```

### Change 5. The shared header of web-auth: move the grey line

File: `web-auth/components/SiteHeader.tsx`, about line 73. This header is used by the Download
and Activation pages.

Before:

```tsx
              {link.label === 'Defect' && index < list.length - 1 ? (
```

After:

```tsx
              {link.label === 'Data Agent' && index < list.length - 1 ? (
```

### Change 6. Docs: the link list and the grey line

File: `docs-site/app/[lang]/layout.tsx`, about line 10.

Before:

```tsx
const NAV_LINKS = [
  { label: 'Defect', href: '/defect' },
  { label: 'Labeler', href: '/labeler' },
```

After:

```tsx
const NAV_LINKS = [
  { label: 'Defect', href: '/defect' },
  { label: 'Data Agent', href: '/data-agent' },
  { label: 'Labeler', href: '/labeler' },
```

File: `docs-site/components/SiteHeader.tsx`, about line 170.

Before:

```tsx
              {link.label === 'Defect' && index < list.length - 1 ? (
```

After:

```tsx
              {link.label === 'Data Agent' && index < list.length - 1 ? (
```

### Change 7. Admin dashboard: the link list

File: `dashboard/frontend/lib/navigation.ts`, about line 9.

Before:

```ts
  links: [
    { label: "Defect", href: process.env.NEXT_PUBLIC_DEFECT_URL || `${site}/defect` },
    { label: "Labeler", href: process.env.NEXT_PUBLIC_LABELER_URL || `${site}/labeler` },
```

After:

```ts
  links: [
    { label: "Defect", href: process.env.NEXT_PUBLIC_DEFECT_URL || `${site}/defect` },
    { label: "Data Agent", href: `${site}/data-agent` },
    { label: "Labeler", href: process.env.NEXT_PUBLIC_LABELER_URL || `${site}/labeler` },
```

The other entries each have a `process.env.NEXT_PUBLIC_..._URL ||` part in front. It lets a
developer point the link at a program running on their own PC. The data agent is not run that
way together with DICE, so I left it out. Without it, nothing has to be added to the
dashboard's `Dockerfile` or to `.env.local.example`.

### Change 8. Admin dashboard: move the grey line

File: `dashboard/frontend/components/SiteHeader.tsx`, about line 70. This file uses double
quotes.

Before:

```tsx
              {link.label === "Defect" && index < list.length - 1 ? (
```

After:

```tsx
              {link.label === "Data Agent" && index < list.length - 1 ? (
```

### Why all four "line" changes belong together with the lists

After changes 2, 5, 6 and 8, a header draws the line only after an entry called Data Agent. A
page whose list was forgotten would then show no line at all. So do the list and the line of
each program in the same change. That is also why I count them in pairs.

---

## The two test files

### Test A. web-auth

File: `web-auth/app/lib/headerNavigation.test.ts`, the last test in the file, about lines 50
to 74. It is named `renders Defect first with a divider before Labeler in LandingPage and
SiteHeader navigation`.

Replace that whole test with this one. Three things differ: the expected list of labels has
the new entry, the expected line stands after Data Agent, and the small list at the end has
the new entry too.

```ts
  it("renders Defect and Data Agent first with a divider before Labeler in LandingPage and SiteHeader navigation", () => {
    for (const lang of ["ko", "en"] as const) {
      const html = renderToStaticMarkup(createElement(LandingPage, { lang, isAuthenticated: true }))
      const navMatch = html.match(/<nav class="dice-nav">([\s\S]*?)<\/nav>/)
      expect(navMatch).not.toBeNull()
      const labels = Array.from(navMatch![1].matchAll(/>([^<]+)<\/a>/g), m => m[1])
      expect(labels).toEqual(["Defect", "Data Agent", "Labeler", "Trainer", "Runner", "Docs", "Download", "Activation"])
      expect(navMatch![1]).toContain(
        '<a href="/defect">Defect</a><a href="/data-agent">Data Agent</a><span class="dice-nav-divider" aria-hidden="true"></span><a href="/labeler">Labeler</a>',
      )
      expect(html).toContain(".dice-nav-divider")
    }

    const siteHeaderHtml = renderSiteHeader({
      navLinks: [
        { label: "Defect", href: "/defect" },
        { label: "Data Agent", href: "/data-agent" },
        { label: "Labeler", href: "/labeler" },
      ],
    })
    const siteNavMatch = siteHeaderHtml.match(/<nav class="dice-nav">([\s\S]*?)<\/nav>/)
    expect(siteNavMatch).not.toBeNull()
    expect(siteNavMatch![1]).toBe(
      '<a href="/defect">Defect</a><a href="/data-agent">Data Agent</a><span class="dice-nav-divider" aria-hidden="true"></span><a href="/labeler">Labeler</a>',
    )
  })
```

The three tests above it in the same file do not mention Defect and stay as they are.

### Test B. Admin dashboard

File: `dashboard/frontend/tests/auth.test.cjs`. Two tests need a change.

**The first** is named `Dashboard header has a local logo, ordered cross-app links, and the
active Admin marker` (about line 212). Two places in it.

The list it passes to the header, before:

```js
    navLinks: [
      { label: "Defect", href: "https://site.test/defect" },
      { label: "Trainer", href: "http://localhost:3030/platform" },
```

After:

```js
    navLinks: [
      { label: "Defect", href: "https://site.test/defect" },
      { label: "Data Agent", href: "https://site.test/data-agent" },
      { label: "Trainer", href: "http://localhost:3030/platform" },
```

The line it expects, before:

```js
  assert.ok(html.includes('<a href="https://site.test/defect">Defect</a><span class="dice-nav-divider" aria-hidden="true"></span><a href="http://localhost:3030/platform">Trainer</a>'))
```

After:

```js
  assert.ok(html.includes('<a href="https://site.test/defect">Defect</a><a href="https://site.test/data-agent">Data Agent</a><span class="dice-nav-divider" aria-hidden="true"></span><a href="http://localhost:3030/platform">Trainer</a>'))
```

**The second** is named `navigation defaults to deployed paths and supports local service URL
overrides` (about line 241). It checks the whole list and then picks entries by their position.
The new entry is second, so every entry after it moves one position.

Before:

```js
    assert.deepEqual(navigation().links.map(link => link.href), ["/defect", "/labeler", "/platform", "/runner", "/docs/ko/guide/overview", "/downloads", "/activation", "/dashboard"])
    assert.deepEqual(navigation().links.map(link => link.label), ["Defect", "Labeler", "Trainer", "Runner", "Docs", "Download", "Activation", "Admin"])
    process.env.NEXT_PUBLIC_SITE_URL = "https://site.test/"
    process.env.NEXT_PUBLIC_TRAINER_URL = "http://localhost:3030/platform"
    assert.equal(navigation().home, "https://site.test/")
    assert.equal(navigation().links[0].href, "https://site.test/defect")
    assert.equal(navigation().links[2].href, "http://localhost:3030/platform")
    assert.equal(navigation().links[4].href, "https://site.test/docs/ko/guide/overview")
```

After:

```js
    assert.deepEqual(navigation().links.map(link => link.href), ["/defect", "/data-agent", "/labeler", "/platform", "/runner", "/docs/ko/guide/overview", "/downloads", "/activation", "/dashboard"])
    assert.deepEqual(navigation().links.map(link => link.label), ["Defect", "Data Agent", "Labeler", "Trainer", "Runner", "Docs", "Download", "Activation", "Admin"])
    process.env.NEXT_PUBLIC_SITE_URL = "https://site.test/"
    process.env.NEXT_PUBLIC_TRAINER_URL = "http://localhost:3030/platform"
    assert.equal(navigation().home, "https://site.test/")
    assert.equal(navigation().links[0].href, "https://site.test/defect")
    assert.equal(navigation().links[1].href, "https://site.test/data-agent")
    assert.equal(navigation().links[3].href, "http://localhost:3030/platform")
    assert.equal(navigation().links[5].href, "https://site.test/docs/ko/guide/overview")
```

What changed in the last block: the two lists got the new entry, the `[2]` became `[3]`, the
`[4]` became `[5]`, and one line was added that checks the new entry at `[1]`.

---

## Checking it before you push

1. **Search once more for places I could not see.** In the top folder of the repo:

   ```bash
   grep -rn "label: ['\"]Defect['\"]" --include=*.ts --include=*.tsx --include=*.cjs . | grep -v node_modules
   grep -rn "=== ['\"]Defect['\"]" --include=*.tsx . | grep -v node_modules
   ```

   **You should see**, before your change: the six lists and the four "line" places named in
   this document, plus the two test files. If the first command prints a file that is not
   named here, that program has a copy of the menu too. It gets the same new line. After your
   change, the second command should print nothing.

2. **Run the web-auth tests.**

   ```bash
   cd web-auth
   npm install
   npm test
   ```

   **You should see:** all tests pass, among them the one from test A.

3. **Run the dashboard tests** the way `dashboard/frontend/package.json` says (look at its
   `"scripts"` block for `test`). I do not have that file, so I cannot name the command.

4. **Look at it.** Start web-auth on your PC (`npm run dev` in `web-auth`) and open the page
   it prints.
   **You should see:** `Defect  Data Agent | Labeler ...`, with the grey line after Data
   Agent, and no line after Defect. The link itself leads nowhere on your PC, because the data
   agent only exists on the DICE address.

---

## How the change reaches the website

This is how I read the two workflow files in `.github/workflows/`. I have not seen them run.

1. **Merge to `main`.** The workflow `Publish Internal` (`helm-publish-internal.yaml`) starts
   by itself when a push to `main` touches `web-auth/`, `docs-site/` or `dashboard/`. It
   builds the changed images (`dice-web-auth`, `dice-docs`, `dice-dashboard-frontend`), writes
   their new tags into the Argo CD Application `dice-stage`, and syncs it.
   **You should see:** the new menu on `https://stage.gtrai.sec.samsung.net/`.
2. **Promote to production.** Start the workflow `Promote Stage to Production`
   (`argocd-promote-production.yaml`) by hand. It asks for two things: `components`, where you
   write `web-auth,docs,dashboard`, and `confirmation`, where you type `PRODUCTION`. It copies
   those tags from `dice-stage` to the Application `dice` and syncs.
   **You should see:** the new menu on `https://dice.gtrai.sec.samsung.net/`.

Nothing in the cluster's settings has to change for this. The link is plain text inside the
images.

**Timing on stage.** On the stage address the link works only once the data agent runs on
stage (Part C of `docs/data-agent-kubernetes-deploy-2026-11-26.md`). Before that, the entry is
shown there but opens a "not found" page. On the production address the data agent already
answers under `/data-agent`, so the link works from the first minute.

---

## What changes for people

- **Everyone who opens DICE sees the entry.** Until now, only people who knew the address
  found the data agent.
- **More people will wait for approval.** A person who clicks the entry and has never used the
  data agent sees "Waiting for approval", and appears in the waiting list on the data agent's
  admin page. Expect more of those requests after this change.
- **The link opens in the same tab**, like the other entries. To come back, people use the
  browser's back button. I found no link back to the DICE main page in the data agent's own
  page.
- **On a narrow window the whole menu is hidden.** All four headers hide the menu entries when
  the window is narrower than 820 pixels. That is so today, and the new entry follows the same
  rule. On a normal screen there is room for one more entry: the entries are short and stand
  26 pixels apart. Look at it once on your own screen all the same (step 4 of
  [Checking it before you push](#checking-it-before-you-push)).

---

## If you want Data Agent before Defect instead

The menu then reads `Data Agent  Defect | Labeler ...`. What differs from the above:

| | After Defect (this document) | Before Defect |
|---|---|---|
| The new line in the six lists | Right after the Defect line | Right before the Defect line |
| Changes 2, 5, 6 (second part) and 8, the grey line | Needed | **Not needed.** The line stays after Defect, which is still the last agent |
| Test A | As written above | Only the list of labels changes: `["Data Agent", "Defect", "Labeler", ...]`. The two expected lines stay as they are today. The name of the test should no longer say "Defect first" |
| Test B, first test | As written above | No change |
| Test B, second test | As written above | The two lists start with the data agent entry, and the positions become `[1]` for Defect, `[3]` for Trainer and `[5]` for Docs |

It is the smaller change. I still prefer "after", because Defect then stays where people are
used to finding it.

---

## What I could not see

- **The Trainer and Labeler programs** (`platform/frontend`, `labeler/frontend`). They are not
  in the copy of the repo I have. If they show a menu with a "Defect" entry of their own, the
  search in [Checking it before you push](#checking-it-before-you-push) finds it.
- **The real files.** My copy is a few days old, and in it every piece of code that starts
  with `on` (such as `onClick`) is missing. None of the lines quoted here is affected, but it
  means I could not start the programs or run their tests. The quoted "before" lines are
  copied from the files. The "after" lines and the changed tests are written by me and have
  not been run.
- **The dashboard's test command**, as said above.
- **Whether the other owners of DICE agree** to a new entry in the shared menu, and to its
  place. The menu belongs to all products on it.

---

## Checklist

- [ ] `web-auth/components/LandingPage.tsx`: new line in the `ko` list
- [ ] `web-auth/components/LandingPage.tsx`: new line in the `en` list
- [ ] `web-auth/components/LandingPage.tsx`: `'Defect'` becomes `'Data Agent'` in the line rule
- [ ] `web-auth/app/downloads/page.tsx`: new line in `NAV_LINKS`
- [ ] `web-auth/app/activation/page.tsx`: new line in `NAV_LINKS`
- [ ] `web-auth/components/SiteHeader.tsx`: `'Defect'` becomes `'Data Agent'` in the line rule
- [ ] `docs-site/app/[lang]/layout.tsx`: new line in `NAV_LINKS`
- [ ] `docs-site/components/SiteHeader.tsx`: `'Defect'` becomes `'Data Agent'` in the line rule
- [ ] `dashboard/frontend/lib/navigation.ts`: new line in `links`
- [ ] `dashboard/frontend/components/SiteHeader.tsx`: `"Defect"` becomes `"Data Agent"` in the line rule
- [ ] `web-auth/app/lib/headerNavigation.test.ts`: the last test replaced (test A)
- [ ] `dashboard/frontend/tests/auth.test.cjs`: two tests changed (test B)
- [ ] The two search commands show nothing unexpected
- [ ] Tests pass, and the page looks right on your PC
- [ ] Merged to `main`, seen on stage, promoted to production
