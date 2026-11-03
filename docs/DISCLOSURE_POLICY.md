# Disclosure policy

Rules for everything that leaves the private working environment of Souls of Muse and becomes public through this repository or the hackathon submission.

The policy has two goals that pull in opposite directions:

1. **Protect** credentials, infrastructure, people and unrelated business from leaking.
2. **Show** reviewers and automated judging tools enough real evidence to understand the scope, depth and honesty of the work.

The answer to both is the same: **publish evidence, not raw material.**

## 1. Scope

The policy covers every outbound channel, not only files:

- files in this repository, including history, release assets and evidence archives;
- commit messages, author metadata, branch names, pull request titles and bodies, issues, review comments;
- the hackathon submission form, demo video, screenshots and slides;
- messages in the hackathon community channels and public social posts that describe the project.

### Everything outbound is public and irreversible

The hackathon Official Rules state that the organizers accept no confidentiality obligations for materials shared in connection with the event. They receive a perpetual, irrevocable licence to host, reproduce, publish and modify them, and a separate perpetual licence to the submission itself. A public repository is also cloned, cached and indexed within minutes. Pushes to `main` additionally produce a timestamped evidence archive of the exact source bytes (see `docs/SOURCE_PROVENANCE.md`).

**Deleting something after publication does not recall it.** Every check in this policy must happen before the push.

By submitting, the project also warrants that the submission is its own original work and infringes no third-party rights, **including privacy rights**. Section 3.6 turns that warranty into checks.

## 2. Classes of information

| Class | Meaning | May leave? |
|---|---|---|
| `PUBLIC` | Written for the public: code, tests, ADRs, reviewer documents, approved media | Yes, after the automated check |
| `PUBLIC-SANITIZED` | Derived from internal material through the templates in `docs/templates/`, with identifiers removed and claims re-verified | Yes, after review and the automated check |
| `INTERNAL` | Working material: tracker tasks, knowledge base notes, agent session logs, dashboards, competitor notes, plans under review | No. Only a sanitized summary may leave |
| `SECRET` | Credentials, account identifiers, infrastructure, personal data of others, legal and financial matters | Never, in any form |

When unsure, treat the item as one class stricter.

## 3. Never publish

### 3.1 Credentials and accounts
- API keys, tokens, cookies, OAuth material, signed or expiring URLs, private keys, `.env` contents.
- Provider account, organisation, project, workspace or advertising account identifiers.
- Budget ledgers, billing exports, per-account spend history. Public programme facts, such as the size of the participant API credit, are fine.

### 3.2 Infrastructure
- Names of machines, nodes and clusters; hostnames, IP addresses, overlay-VPN names, ports.
- Local usernames and file system paths (`/Users/<name>/…`, home directories, vault locations).
- Lists of installed services, runtime directories, process layouts.
- Security reviews, incidents, suspicious-mail investigations, access-control details.

### 3.3 Private workspaces and link-only shares
- Links to or identifiers from the task tracker, chat servers and channels, the knowledge base, shared documents.
- **Link-only shares** (dashboards, preview deployments, shared AI conversations or artifacts, cloud documents "visible to anyone with the link"). Inside a public repository a link-only page becomes a public page.
- Agent session identifiers and internal run identifiers.

### 3.4 Raw agent material
- Session transcripts, system prompts and agent profiles, memory files, orchestration instructions, raw tool logs.
- Use the journal template (`docs/templates/JOURNAL_ENTRY.md`) to publish *what was decided, how it was verified and what failed*, not the transcript.

### 3.5 People
- Contact details of anyone: e-mail addresses, phone numbers, messenger handles, postal addresses.
- Names, account names, faces, voices or messages of community members, signatories of the Convention, students, teachers, partners or advisers, unless that person has given documented consent for this specific use.
- Anything about minors.
- Other hackathon participants' projects, messages or metrics taken from community channels. Describe the competitive landscape only in aggregate ("several voice-practice projects exist"), never with names or links.

### 3.6 Third-party rights
Before publishing any asset, record its origin and licence in the component's `BASELINE.md` or the media section of `docs/workstreams/06-media.md`:
- media produced by tools other than the Meta models being credited (for example a third-party video agent) must be labelled with the real tool and checked against that tool's terms;
- historical artworks, photographs, fonts, music and samples need a public-domain or licence basis;
- name-to-notation cards or signatures of real people are personal data (3.5).

### 3.7 Business, legal and unrelated work
- Company formation, partners and negotiations, investment and pricing models not approved for publication, legal analyses.
- Any work that is not part of the Souls of Muse hackathon project, even if it sits in the same tracker range or on the same dashboard.

## 4. What to publish for reviewers

Judging weights (Official Rules): **Impact 30%**, **Use of Meta AI tooling 25%**, **Technical depth and execution 20%**, **Demo 25%**. Every public document should help a reviewer score one of them. `docs/FOR_REVIEWERS.md` is the map.

| Criterion | Publish | Source class |
|---|---|---|
| Impact | Mission, who benefits, problem statement, community growth as aggregate counts, governance principles | `PUBLIC`, `PUBLIC-SANITIZED` |
| Meta tooling | Per model: role in the system, tasks it performed, how its output was checked, capabilities discovered, limits hit. Built from the agent-journal registry through the journal template | `PUBLIC-SANITIZED` |
| Technical depth | Code, tests, ADRs, failure analyses, retracted claims and what replaced them | `PUBLIC`, `PUBLIC-SANITIZED` |
| Demo | Live URL, demo video, an exact list of what is real and what is simulated | `PUBLIC` |
| Process (supports all) | Timeline, pre-event vs event boundary, human vs AI attribution, provenance evidence | `PUBLIC` |

Dead ends, corrections and retracted claims are evidence of rigour. Publish them in sanitized form instead of hiding them.

## 5. Claims must be verifiable

Every capability statement uses exactly one status:

| Status | Meaning | Evidence required |
|---|---|---|
| **Working** | Verified end to end in a real environment | Reproducible steps, live URL or recording |
| **Prototype** | Runs; simulated parts are named | List of simulated parts |
| **Offline-tested** | Unit or integration tests pass without live services | Test command and count |
| **Designed** | Specification or plan exists, not built | Link to the design document |
| **Planned** | Intended, not started | None |

Rules:
- No status without evidence in this repository or in the submission.
- Numbers (test counts, latencies, costs, participants) state their source and date; estimates say "estimated".
- Model names are written as the vendor publishes them. Work by other tools is never credited to Meta models.
- A claim that was published and later found wrong is corrected in place with a dated note, never silently edited away.
- The scope the owner set as mandatory for the submission (voice for both lesson participants, real lesson hours in agent journals, tactile metronome) is claimed only at the status actually verified on submission day.

## 6. Pre-event and event work

Participants may build on an existing product if the new contribution is identified. Organizer guidance also asks for a clear separation of what existed before the event.

- `docs/HACKATHON_CONTRIBUTIONS.md` holds the table of what existed, what changed and what is new.
- Each component built on earlier work carries a `BASELINE.md` (`docs/templates/BASELINE.md`): a description of the pre-event state, optional screenshots and a content hash. Pre-event source code is not published.
- Code written during the event is published in full. Modified pre-event files are published as diffs, or in full with the changed parts marked.

## 7. Naming people, agents and systems

- **Project owner:** by name, as in `README.md`.
- **Other people:** by role ("music teacher", "community member") unless 3.5 consent exists.
- **Meta models** (Muse Spark, Muse Wonder, Muse Image, Voice Transcribe, SAM 3.1): by product name. This is required for the Meta tooling criterion.
- **Other AI tools:** by product name where they contributed, so that Meta models are not over-credited.
- **Internal agent call signs** (short codes used inside the team) may appear only as attribution labels. Never combine them with machine names, paths or accounts. Prefer roles in new text: "implementation agent", "independent reviewer", "integrator".
- **Machines and environments:** "the development workstation", "a single persistent VM". No real names.

## 8. Moving internal material out

Never paste internal text into a public file. Rewrite it from the template and replace identifiers as follows:

| Internal item | Public replacement |
|---|---|
| Tracker issue ID or link | Workstream name and date, for example "Workstream 03, 30 Oct 2026" |
| Local path | `<workspace>/…` or the repository-relative path |
| Machine or node name | "development workstation" or "persistent VM" |
| Chat or channel link | "organizer guidance in the community FAQ, 26 Oct 2026" |
| Session or run ID | "session S-1, S-2 …" numbered inside the document |
| Personal name (no consent) | Role |
| Exact spend or account data | Omit, or a rounded aggregate if approved |
| Hash of an internal file | Omit, unless the file itself is published |

Then re-check every claim against section 5 and run the automated check.

## 9. Release procedure

1. **Author** (any agent or person) prepares the material from a template.
2. **Disclosure review:** the designated reviewer (currently the Claude Code agent) reads every changed line against this policy. All outbound reports pass through this step, including those built from the agent-journal registry.
3. **Automated check:**
   ```sh
   python3 scripts/disclosure_check.py
   python3 scripts/disclosure_check.py --commits origin/main..HEAD
   ```
4. **Draft pull request.** The title and body are public too and are written to this policy.
5. **Owner approval:** the project owner approves the merge.
6. **Merge to `main`.** This triggers the timestamp evidence workflow and cannot be undone.
7. **Before the submission:** run `python3 scripts/disclosure_check.py --release`, which also fails on unfilled `<!-- FILL … -->` placeholders.

History on `main` is never rewritten: timestamp evidence depends on it.

### If something leaks
1. Revoke or rotate any exposed credential **first**. Assume it is already copied.
2. Remove the material in a new commit and note the removal internally.
3. Do not attempt a history rewrite on `main`. Forks, caches and organizer copies cannot be recalled.
4. Record what happened in the internal tracker (not in this repository) and add a check that would have caught it.

## 10. Automated check

`scripts/disclosure_check.py` (standard library only, tested in `tests/test_disclosure_check.py`) scans tracked text files and, optionally, commit metadata for:

credentials and tokens · personal home paths and local-file links · private and overlay-VPN IP ranges · personal e-mail addresses and phone numbers · links into private workspaces and link-only shares · internal tracker identifiers · terms from the **private denylist**.

The private denylist holds internal names: machines, people, partners, internal projects. A public list of those names would itself be a leak, so it lives outside the repository:
- locally in `private/disclosure-denylist.txt`, which is git-ignored;
- in CI as the repository secret `DISCLOSURE_DENYLIST`, one term per line.

The script never prints denylist terms and masks detected secrets in its output.

A line may be exempted with the marker `disclosure: allow <rule>` and a reason. Every marker is a review item. Markers are never used for real credentials, paths or personal data.

The check is a safety net, not a substitute for section 9 step 2: it cannot recognise a confidential sentence written in plain words.

## 11. Open owner decisions

- Whether internal agent call signs stay in attribution text or are replaced by roles everywhere.
- Whether the submission uses this repository with explicit pre-event/event separation, or a separate extract repository.
- Consent status for any real person's name or notation card shown in the demo.
