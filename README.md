# DVERA — CT Verification Skills for C/C++ Coding Agents

> 한국어: [README.ko.md](README.ko.md)

DVERA (Dynamic Verification Agent) brings CT C/C++ verification work into coding agents such as Claude Code, Codex CLI, Cursor, and GitHub Copilot. It uses the working context of source code, requirements, build information, source changes, and existing test assets to prepare and request CT verification work.

CT (Controller Tester) is a test automation solution for unit, integration, and code-based testing of mission-critical C/C++ software. It brings together test-environment setup, test design and generation, execution, code-coverage analysis, reporting, and traceability management.

DVERA does not replace CT's verification results. The coding agent helps prepare and coordinate verification work; CT performs the analysis, build, test execution, and result aggregation. Generated tests must be reviewed for test intent, data, and expected results, then confirmed with actual execution results and measured coverage.

## What the CT and DVERA workflow adds

| Verification need | CT and DVERA workflow |
|---|---|
| Complex C/C++ environments | Capture compiler, macro, include-path, toolchain, build, and target conditions before analysis. |
| Unit and integration verification | Design and execute tests at function, module, and interface levels, including existing GoogleTest assets where applicable. |
| Reviewable evidence | Connect test intent, execution results, statement/branch/MC/DC coverage, reports, and requirement links for review. |
| Repeated change verification | Re-run affected tests after code changes and review new failures and coverage deltas for regression follow-up. |
| AI-assisted test work | Use code, requirements, and change context to prepare test work, then improve it with CT analysis and measured results. |

## Workflow at a glance

1. Prepare the compiler, macro, include-path, toolchain, and target context for a CT project.
2. Analyze the project and resolve environment or configuration issues through a controlled feedback loop.
3. Generate, execute, and improve unit or integration tests using build, execution, and coverage feedback.
4. Review coverage and results, produce reports, and re-run affected verification after source changes.

The Skills in this repository document that product-connected workflow. They are not standalone replacements for a CT installation.

## Install

In Claude Code:

```text
/plugin marketplace add SuresoftTechnologies/dvera-plugin
/plugin install dvera@suresofttech
```

Or from a terminal:

```text
claude plugin marketplace add SuresoftTechnologies/dvera-plugin
claude plugin install dvera@suresofttech
```

Skills then load as `/dvera:ct-init-project`, `/dvera:ct-test-loop`, and so on. The plugin adds about 620 tokens to every session; each Skill body is read only when that Skill runs.

Product-backed actions need a deployed CT environment. Without one, a Skill stops at its installation check and shows how to reach product support.

## Example requests

Trigger examples from the CT user guide. Responses can vary with the AI model and conversation context; if the result differs from what you expect, rephrase the request with more detail and retry.

| Request | Skill |
|---|---|
| `Create a CT project and start verification.` | `ct-init-project` |
| `Run tests in CT.` | `ct-init-project` |
| `Generate tests for the calculate_checksum function.` | `ct-test-loop` |
| `Find functions without tests and generate tests for them.` | `ct-test-loop` |
| `Run regression tests.` | `ct-regression` |
| `Open CT.` | `ct-open` |

## Skills

All Skills require a deployed CT environment for their product-backed actions and stop with an installation notice when none is found.

| Skill | CT workflow stage |
|---|---|
| `ct-init-project` | Start or prepare a CT verification project. |
| `ct-extract-macro` | Capture target compiler macros and build-environment facts. |
| `ct-make-conf` | Prepare the analysis configuration for the selected toolchain. |
| `ct-setup-project` | Create the CT project and apply build inputs. |
| `ct-analysis-loop` | Analyze the project and resolve configuration or toolchain issues. |
| `ct-test-loop` | Generate, run, and improve tests. |
| `ct-kb-update` | Record verified workflow observations after a completed CT run. |
| `ct-regression` | Re-run existing tests after a code change and review deltas. |
| `ct-self-healing` | Run regression evidence collection and identify CT Self-Healing review candidates. |
| `ct-run-gtest` | Re-run GoogleTest assets registered in CT and review results and coverage. |
| `ct-req-to-test` | Generate and execute a CT AI test from approved requirements. |
| `ct-report` | Export execution and coverage evidence. |
| `ct-open` | Open the CT project for visual inspection. |
| `ct-orchestrator` | Resume the appropriate stage of an in-progress verification workflow. |

## Product-backed workflow

DVERA works with a deployed CT and DVERA environment. This repository documents the verification workflow, but does not include the CT runtime, product installation, or direct product integration.

Without the deployed environment, users can inspect this repository's documented workflow, but a Skill that needs CT actions stops at its installation check. It must not claim that CT analysis, execution, coverage measurement, or reporting has occurred.

## Requirements for product-backed verification

- CT 2026.06 or later
- A valid CT license
- A supported C/C++ build and target environment
- DVERA integration supplied as part of the deployed CT environment

For a product demo, purchase, or deployment consultation, contact [bizcenter@suresofttech.com](mailto:bizcenter@suresofttech.com).

## License and trademarks

This repository is licensed under the [MIT License](LICENSE). The license covers only the documentation and Skill files in this repository. CT and DVERA are Suresoft Technologies products; product functionality and product licensing are not granted by this repository.

GoogleTest is a trademark of Google LLC. This repository is not affiliated with, sponsored by, or endorsed by Google. Other product names may be trademarks of their respective owners.
