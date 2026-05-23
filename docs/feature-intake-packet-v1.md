# Feature Intake Packet v1

## Purpose

The Feature Intake Packet is the canonical input document for the SDLC Orchestrator. It captures the minimum structured context needed to decide whether a feature request is ready to move into downstream workflow generation.

This packet is intentionally documentation-focused. It does not assume a backend, database, authentication layer, external integrations, or AI provider implementation. Its job is to create a clean, portable structure that later milestones can consume.

## Design Goals

- Normalize feature requests into a repeatable structure.
- Separate facts from assumptions and unknowns.
- Make readiness visible before generating downstream artifacts.
- Reduce accidental over-generation from incomplete requirements.
- Provide a schema that can be validated by future services.

## Core Principle: Separate Facts, Assumptions, and Missing Details

Every major section in the packet uses the same field shape:

```json
{
  "value": "...",
  "confidence": "high | medium | low",
  "source": "provided | inferred | missing",
  "needs_clarification": true
}
```

This separation matters because downstream SDLC outputs are only as trustworthy as their inputs.

- `value` stores the current best-known statement.
- `confidence` indicates how reliable that statement is.
- `source` distinguishes whether the content was explicitly provided, inferred from context, or still missing.
- `needs_clarification` flags whether a human follow-up is still needed even if a draft value exists.

If a field is inferred, it can still be useful for draft generation, but it should not be treated as settled fact. If a field is missing, downstream generation should either pause or clearly mark the gap.

## Packet Structure

The Feature Intake Packet includes these required sections:

- `feature_name`
- `problem_statement`
- `business_goal`
- `target_users`
- `current_behavior`
- `desired_behavior`
- `in_scope`
- `out_of_scope`
- `business_rules`
- `data_inputs`
- `data_outputs`
- `user_roles_permissions`
- `systems_impacted`
- `api_or_contract_impacts`
- `ui_impacts`
- `reporting_or_audit_needs`
- `error_handling_expectations`
- `edge_cases`
- `non_functional_requirements`
- `dependencies`
- `known_risks`
- `open_questions`
- `assumptions`

The packet also includes readiness metadata:

```json
{
  "readiness_score": 0,
  "can_continue": false,
  "blocking_gaps": [],
  "safe_to_generate": [],
  "not_safe_to_generate": []
}
```

## How Readiness Should Be Calculated

Readiness scoring should be simple, explainable, and conservative.

### Recommended scoring approach

Use a weighted checklist rather than a complex formula. Start from 100 and subtract points for missing or weak critical areas.

Suggested weighting:

- Problem clarity: 15 points
- Business intent clarity: 10 points
- Scope clarity: 15 points
- Behavior clarity: 15 points
- Rules and constraints clarity: 10 points
- Impact analysis clarity: 10 points
- Validation and failure expectations clarity: 10 points
- Dependencies and risks clarity: 10 points
- Open questions severity: 5 points

### Practical scoring rules

- Treat `source: missing` as a stronger penalty than `source: inferred`.
- Treat `needs_clarification: true` on critical fields as a material penalty.
- Do not assign high scores when core delivery details are inferred instead of provided.
- Reduce the score when blocking gaps would make generated outputs misleading or unsafe.

### Readiness bands

- `90-100`: Generate full SDLC package.
- `70-89`: Generate draft package with assumptions clearly marked.
- `50-69`: Generate discovery summary and clarification questions only.
- `0-49`: Stop and request better input.

## Critical Fields by Downstream Use

### Critical before generating Jira stories

These fields should be dependable before story generation:

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
- `open_questions`
- `assumptions`

Why: stories need clear intent, actors, scope boundaries, and impacted systems to avoid producing incorrect backlog items.

### Critical before generating test cases

These fields should be dependable before test generation:

- `desired_behavior`
- `business_rules`
- `data_inputs`
- `data_outputs`
- `user_roles_permissions`
- `error_handling_expectations`
- `edge_cases`
- `non_functional_requirements`
- `api_or_contract_impacts`
- `ui_impacts`

Why: test cases depend on observable behavior, rules, permissions, inputs, outputs, and failure modes.

### Critical before generating automation recommendations

These fields should be dependable before automation recommendations:

- `systems_impacted`
- `api_or_contract_impacts`
- `ui_impacts`
- `reporting_or_audit_needs`
- `error_handling_expectations`
- `non_functional_requirements`
- `dependencies`
- `known_risks`

Why: automation recommendations must reflect real touchpoints, constraints, and operational risks rather than just the feature narrative.

## Example of a Good Packet

A good packet does not need every answer to be perfect, but it does need strong clarity in core areas:

- The feature and business goal are concrete.
- Current and desired behavior are distinguishable.
- Scope boundaries are explicit.
- At least the primary business rules are known.
- Impacted systems and dependencies are named.
- Open questions are visible instead of hidden.
- Assumptions are clearly labeled and not mixed with facts.

See [example-feature-intake-packet-v1.json](/C:/Users/wolf-ai/Workspace/sdlc-orchestrator/docs/example-feature-intake-packet-v1.json) for a complete example.

## Example of Blocking Gaps

Examples of gaps that should lower readiness or stop downstream generation:

- No clear problem statement.
- No defined desired behavior.
- Scope is broad but not bounded.
- User roles are unknown for a permissions-sensitive feature.
- Systems impacted are unknown for an integration-heavy feature.
- Error handling expectations are absent for a workflow that affects customers or operations.
- Key dependencies are unknown but the feature requires cross-team delivery.

## Packet Authoring Guidance

Keep entries short, specific, and operational.

- Prefer bullet-style statements inside `value` fields when multiple facts are needed.
- Do not hide uncertainty; use `source` and `needs_clarification`.
- Avoid filling gaps with confident prose.
- Use `blocking_gaps` to state what prevents safe downstream generation.
- Use `safe_to_generate` and `not_safe_to_generate` to communicate boundaries clearly.

## Intended Use in Future Milestones

Later milestones can use this packet as the single normalized source for:

- backlog generation
- clarification workflows
- test planning
- risk review
- automation recommendation workflows

This keeps orchestration consistent even as the implementation surface grows.
