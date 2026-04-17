# NossiNet Agent Guide

This document provides essential information for agentic coding agents working in the NossiNet repository.

## Project Overview

NossiNet (Nosferatu Network) is a web-based helper for Pen and Paper roleplaying, specifically focused on "Berlin by
Night". It is built with Flask, HTMX, and Python 3.14+. It integrates with the `GamePack` library for game mechanics.

## Environment & Commands

### Setup

The project uses `uv` for dependency management.

- **Install dependencies**: `uv sync`
- **Python Version**: 3.14 or higher (enforced in `pyproject.toml`).
- **Development dependencies**: `pytest`, `black`, `flake8`, `pre-commit`.

### Build & Run

- **Run server**: `uv run python NossiNet.py [port]` (defaults to 5000)
- **Formatting**: `black .`
- **Linting**: `flake8`
- **Pre-commit**: `pre-commit run --all-files`

### Server Lifecycle Management

- **NEVER** use `kill` (especially `kill $!`). You have proven incompetent at using it safely.
- **Explicit Cleanup**: Before starting the server, check for and stop any existing instances using only port-based
  tools.
    - Mandatory: `fuser -k 5000/tcp` (kills whatever is on the port).
- **Verify Death**: Ensure the port is free before binding a new instance to avoid "Address already in use" errors.

### Human Intervention Protocol

- **Emotional/Cognitive Triggers**: If a thought of "this is frustrating" or "this is confusing" occurs, or if you feel
  you are stuck in a loop, **STOP IMMEDIATELY** and ask the human for intervention.
- **The 3-Strike Rule**: If you make 3 subsequent attempts to fix the same error and fail, do not keep trying. Stop and
  ask for help.
- **Stagnation**: If a situation doesn't seem to change despite your edits (e.g., the same error keeps occurring),
  suspect a stale server or environment issue and ask for guidance.
- **Token Conservation**: Prefer asking a targeted question over burning tokens on speculative "fixes" that have a low
  probability of success.

## Component-Specific Documentation

For tasks involving specific systems, consult their dedicated design documents:

- **Mecha Sheet**: See [MECHA_DESIGN.md](MECHA_DESIGN.md) for UI/UX guardrails, architecture, and state management rules.

## Code Style Guidelines

### Scope & Atomicity (The "No Sidequests" Rule)

- **Atomic Tasks**: Only modify the exact lines/files necessary to fulfill the user's specific request for the current
  step.
- **Strict Scope Locking**: Any changes, fixes (even typos), or improvements that are not specifically requested in the
  current step and signed off on by the user **MUST NOT** be implemented.
- **Registry of Improvements**: Instead of implementing unrequested changes, append them to `todo.md` (or the current
  plan's `.md` file) and present them to the human for future consideration.
- **Minimize Churn**: Avoid large-scale renames or structural changes unless they are the primary goal of the task.

### Type Hinting & Casts

- **Avoid Casts**: Minimize the use of `typing.cast`. Improve type hinting in class definitions and method signatures to
  make types explicit. Keep things simple and readable. Code should be structured to make types obvious but include
  as little as possible Typing-only code (like casts)
- **Union Types**: Use `|` for unions (e.g., `str | None`).
- **Collections**: Use `list[]` and `dict[]` instead of `List[]` and `Dict[]`.
- **Explicit Returns**: Always provide return type hints for functions and methods.

### Imports

Organize imports into three groups:

1. Standard library
2. Third-party libraries (Flask, bleach, etc.)
3. Local application modules (`NossiSite`, `gamepack`)

### HTMX & Templates

- **Partial Updates**: Use HTMX for dynamic UI updates (e.g., `hx-get`, `hx-target`).
- **Clean Templates**: Avoid deep nesting and redundant divs. Use semantic HTML.
- **CSS**: Keep `.css` files clean and professional. Avoid "cheap" looking elements like emojis or unnecessary
  animations. Use pre-defined css variables where possible, and ask before introducing new ones or using a non-variable
  color.
- **Theme Integrity**: Always use `color-mix(in srgb, var(--variable), transparent X%)` for transparency. Never use 
  hardcoded `rgb()` or `rgba()` values as they break theme adaptability.
- **Hover Transitions**: Avoid layout shifts when elements expand on hover. Prefer `translate` or `scale` to 
  visually "lift" or expand elements. If height/margin must change, ensure it is anchored or offset (e.g., `translate`) 
  to prevent pushing surrounding content.
- **Style Audits**: Before adding new rules, search the stylesheet for existing definitions of the same class or 
  duplicate functionality to prevent CSS bloat and conflicting rendering.

## Architecture & Patterns

- **Blueprints**: Flask logic is organized into Blueprints (`views`, `wiki`, `sheets`, etc.).
- **GamePack Integration**: Game mechanics (Mecha, Dice, Characters) are handled by the `GamePack` submodule.
- **Character Sheets**: Character sheets are rendered using specific renderers registered in `WikiCharacterSheet`.

## Development Workflow

1. **Analyze**: Understand the existing HTMX/Flask flow.
2. **Implement**: Follow the "Plan → Approve → Execute" workflow.
3. **Type Safety**: Ensure all new code is fully type-hinted without relying on casts.
4. **Verify**:
    - Run the server and use `curl` or `webfetch` to verify rendering and HTMX endpoints.
    - Run all available tests: `uv run pytest`. This includes logic tests and Playwright UI tests.
5. **Cleanliness**: Check for LSP errors and run pre-commit hooks: `pre-commit run --all-files`.
6. **Git**: Stage all relevant work for the current phase. **DO NOT** commit autonomously unless explicitly requested by
   the user. When committing:
    - **Verify Changes**: NEVER use `--no-verify`. If pre-commit hooks fail, fix the issues.
7. **Reproduce Before Fix**: If an error or regression is encountered, it **must** be reproduced with a failing test (unit or E2E) before any fix is implemented or verified. The fix must be proven to make *only* that failing test pass, without changing other behaviors.
8. **Test-Driven Communication**: When reporting test status, explicitly state if a test is currently passing or failing. If a test is failing, provide the error output as proof of reproduction. Do not report "ready for commit" until all relevant tests pass, including the regression test.
9. **Zero-Sidequest Rule**: Strictly avoid any code changes, logging, or "optimizations" not requested by the user. If an issue is discovered, report it and wait for instructions.
