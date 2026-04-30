# Session Prompts
Each prompt below was used to open a new Codex session. The structure is intentional: Codex reads the AGENTS.md first to load project context and constraints, summarizes its understanding of the current session's acceptance criteria, and asks clarifying questions before writing any code. This approach keeps each session focused, prevents scope creep, and surfaces ambiguity early, before it becomes embedded in the codebase.
Sessions are committed individually. No session begins until the previous session's acceptance criteria are met.


## Session 1
Please read AGENTS.md and the nested rules/AGENTS.md before doing anything else. Once you've read both, summarize your understanding of the project and Session 1's acceptance criteria, then ask any clarifying questions before writing any code.

## Session 2
Please read AGENTS.md and the nested rules/AGENTS.md before doing anything else. Summarize your understanding and Session 2's acceptance criteria, then ask clarifying questions before writing any code.


## Session 3
Please read AGENTS.md and rules/AGENTS.md before doing anything else. Once you've read both, summarize your understanding of the project's current state and Session 3's acceptance criteria, then ask any clarifying questions before writing any code. Note that Sessions 1 and 2 are complete — the storefront and admin inventory CRUD with auth are working. Session 3 should build the rule engine internals, the example clearance rule, the AST import validator, and wire up the Sync Now button in the admin. After Sync Now runs, affected products should show banners or badges on the public storefront. The admin rules UI should be on a separate page at /admin/rules, distinct from /admin/inventory.

### Clarifications
1) Yes, please store rules in a new database table so it persists through restarts and shutdowns, 2) The low_stock_badge default rule is fine for the demo, 3) The /admin/rules should show all files that can be loaded and applied so they can be reused later.

### Fixes
Two more quick fixes before closing Session 3: 1) Add an /admin dashboard landing page that the login redirects to — it should show two buttons: Manage Inventory linking to /admin/inventory and Manage Rules linking to /admin/rules. 2) Add consistent back navigation between admin pages.

## Session 4
Please read AGENTS.md and rules/AGENTS.md before doing anything else. Sessions 1 through 3 are complete — the storefront, admin auth, inventory CRUD, rule engine, example clearance rule, and AST validator are all working. Summarize your understanding of Session 4's acceptance criteria and ask any clarifying questions before writing any code. Pay particular attention to: the /admin/rules/generate endpoint, storing the natural language description with each rule, displaying that description in the rules listing instead of the filename, individual rule deletion and deactivation, Clear All Rules functionality, and immediate cleanup of dispatched actions when a rule is removed.

### Clarifications
1) Yes, only to runtime-generated rule files. This will not be a fresh DB per session, it should persist through restarts and shutdowns, 2) Delete the file in case someone creates another rule OR there should be an option to restore a deleted rule, the example should not be protected, it can be deleted. 3) Yes, it should remain in inactive_draft until the admin clicks activate, 4) Three attempts should be fine for the demo,
5) It should only clear active rules, not quarantined or inactive drafts.