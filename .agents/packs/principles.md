# Principles

Every m3trik repo follows these, whatever its language. One line each; the rationale is CODE_STANDARD (`§N`: `m3trik/docs/CODE_STANDARD.md` in the workspace, else https://github.com/m3trik/m3trik/blob/main/docs/CODE_STANDARD.md). A language pack spells them for that language; a repo's own AGENTS.md adds its shapes.

## Shape
- **One shape at every scale** (§0): a unit has one charter, a surface others touch, a host-free model under host adapters, parts in a declared order, seams, contracts and proof.
- **Libraries hold the logic, products the UI** (§14): a panel calls a library's API, never a host.
- **Contracts are declared once, as data**, in the lowest unit every reader reaches; other languages get generated types, and every restatement is checked.
- **Public APIs are contracts** (§5): a removed or renamed public name gets a moved-names row naming its new home (a deprecation alias with a real `remove_in` only where callers need a window), a CHANGELOG line and a minor bump. Saved data (scenes, presets, manifests, serialized fields) is always published.

## Design
- **Composable primitives** over one-offs: public APIs take plain values (str, dict, callable) and hide factories.
- **SOLID via composition**: extend through hooks, registries and strategy callables, never by editing stable paths or growing conditional trees; pass collaborators in. A large object is a facade over small collaborators; mixins only for capabilities several classes share.
- **Host behavior is injected**: a small adapter interface beside the model with a `Pure*` default, never a per-host subclass.
- **YAGNI**: no speculative features. **Unify over duplicate**: a drift-guarded vendored copy is the one sanctioned duplicate (§6).
- **Adopt before building** (§15): first look for what already does the job (our APIs, the host's built-ins, an open standard, a maintained library); use it when it fits our needs, licenses and dependency rules, else build and say why.
- **Tools behave as their users already expect** (§15): the host's conventions, progress and cancel, undo, preview, fixable errors, open formats that pass their reference validators. Deviate only with a stated reason.
- **Export is plug-and-play; previews overlay, never replace** (§13).

## Work
- **Session safety (hard rule)**: never connect to, test against or overwrite an application session a person opened (Maya, Blender, Unity, Painter...). Launch a new instance first; later runs, tests included, may reuse an instance the tooling launched and still owns while no other run is using it, after reloading changed code; run headless wherever possible.
- **Issue-driven TDD** (§9): reproduce the bug, write the failing test (red first), fix, verify; the test stays. After a change, run the affected tests and report the real result.
- **Findings: fix now.** A mechanical or minor finding is fixed in the turn that found it; a genuine deferral is logged in the backlog, never left in chat. Fix every sibling copy of a repeated shape, or log each.
- **Instructions stay small and stable**: actionable rules only; no work history, dates or counts (churn defeats prompt caching).
- **English only**, test data included. **Public-repo hygiene** (§11): no client names or paths.
