# AI tool disclosure

## Summary

AI was used as a **code assistant** while developing Waypoint's **backend and frontend**, across all four
roles (dispatcher, store manager, loader and driver). It helped write and edit code, tests and supporting
files, and helped run checks on them.

## What AI did not do

The team made the architectural decisions and every other decision without AI assistance. This covers:

- reading the challenge and choosing what to build and what to leave out;
- the system architecture: the split between the API, the database and the web app, the data model, the
  planning approach and the rules it enforces;
- the user experience design for every role;
- reviewing, Writing, testing and accepting the code, and deciding what was merged and submitted;
- the demo video.

## How it was used

1. A team member described a task in plain language, for example a screen to build, a rule to implement or
   a bug to fix.
2. The assistant proposed or wrote the code.
3. The team member reviewed it, ran the application and the tests, and either accepted the change or asked
   for another one.

The assistant was a tool in the development process. The team owns the design and the resulting code.

## November 2026 audit and Datathon integration update

Codex assisted with this repository audit, requirements reconciliation, copying and adapting
Datathon code, the compact Task 1 candidate, separate inference API, UI/profile fixes, tests,
notebook source, and architecture/deployment documentation. It ran the local validation commands
reported in the current verification document. The earlier statement that every architecture,
review and testing decision was made without AI does not describe this later work. The team
must review these changes and supply accurate authorship/history for its original modelling,
designs and submission videos; those activities are not inferred here.
