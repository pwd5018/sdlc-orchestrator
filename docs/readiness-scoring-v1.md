# Readiness Scoring v1

## Purpose

Readiness scoring answers a simple question: is the intake packet complete and trustworthy enough to generate downstream SDLC outputs?

The score is not meant to imply delivery size or business value. It only reflects input quality and downstream safety.

## Why Facts, Assumptions, and Missing Details Must Be Separated

Downstream generation can fail in subtle ways when unknowns are presented as facts.

- Facts support reliable story and test generation.
- Assumptions can support draft outputs, but must be marked clearly.
- Missing details should drive clarification, not confident generation.

If these categories are mixed together, the orchestrator may produce convincing but misleading artifacts.

## Recommended Scoring Method

Use an explainable weighted assessment across a small set of dimensions. A lightweight scoring model is easier to audit and easier to improve later.

### Suggested dimensions

- Problem definition
- Business objective clarity
- Scope definition
- Functional behavior clarity
- Rules and constraints
- Data and permissions clarity
- System and integration impact clarity
- Validation, audit, and failure expectations
- Dependencies, risks, and unresolved questions

### Suggested scoring behavior

- Award higher scores when fields are `provided`, high-confidence, and do not need clarification.
- Award partial credit when fields are `inferred` but usable.
- Award low or no credit when fields are `missing` or materially ambiguous.
- Apply stronger penalties to missing critical fields than to optional detail gaps.

## Readiness Thresholds

### 90-100

Generate the full SDLC package.

Expected condition:

- Core requirements are clear.
- Scope is bounded.
- Major impacts are known.
- Few or no blocking gaps remain.

### 70-89

Generate a draft SDLC package with assumptions clearly marked.

Expected condition:

- Core intent is mostly clear.
- Some delivery details are inferred or still need clarification.
- Generation is useful, but should not be treated as final.

### 50-69

Generate only a discovery summary and clarification questions.

Expected condition:

- Enough context exists to discuss the feature.
- Not enough certainty exists to safely produce stories, tests, or automation guidance.

### Below 50

Stop and request better input.

Expected condition:

- Core problem, desired behavior, or scope is too unclear.
- Any generated delivery artifact would be more speculative than useful.

## Critical Fields Before Generating Jira Stories

These fields should usually be strong before backlog generation:

- `feature_name`
- `problem_statement`
- `business_goal`
- `target_users`
- `current_behavior`
- `desired_behavior`
- `in_scope`
- `out_of_scope`
- `business_rules`
- `systems_impacted`
- `dependencies`

If several of these are weak or missing, the orchestrator should avoid story generation and ask questions first.

## Critical Fields Before Generating Test Cases

These fields should usually be strong before test case generation:

- `desired_behavior`
- `business_rules`
- `data_inputs`
- `data_outputs`
- `user_roles_permissions`
- `error_handling_expectations`
- `edge_cases`
- `non_functional_requirements`

If these are incomplete, generated tests risk validating the wrong behavior or missing critical edge conditions.

## Critical Fields Before Generating Automation Recommendations

These fields should usually be strong before automation recommendations:

- `systems_impacted`
- `api_or_contract_impacts`
- `ui_impacts`
- `reporting_or_audit_needs`
- `error_handling_expectations`
- `non_functional_requirements`
- `dependencies`
- `known_risks`

Automation guidance should be grounded in actual system touchpoints and operational constraints, not generic patterns.

## Example of a Good Packet

A good packet:

- describes a specific business problem
- names the intended users
- differentiates current behavior from desired behavior
- makes scope boundaries explicit
- captures at least the main rules, dependencies, and risks
- identifies what is known versus assumed

See [example-feature-intake-packet-v1.json](/C:/Users/wolf-ai/Workspace/sdlc-orchestrator/docs/example-feature-intake-packet-v1.json).

## Example of Blocking Gaps

Blocking gaps are issues that make downstream generation unsafe or misleading.

Examples:

- Desired behavior is not defined.
- Impacted systems are unknown, but the feature changes cross-system workflows.
- User roles and permissions are missing for an access-sensitive feature.
- Error handling expectations are absent for a customer-facing flow.
- Scope includes multiple teams, but dependencies are unknown.

## Suggested Output Behavior by Score

Use the score to guide what the next milestone is allowed to produce:

- `90-100`: Jira stories, acceptance criteria, test cases, and automation recommendations may all be generated.
- `70-89`: The same outputs may be generated as drafts, with assumptions explicitly listed.
- `50-69`: Only discovery notes, clarification prompts, and readiness feedback should be produced.
- `0-49`: The workflow should stop and request stronger intake input.
