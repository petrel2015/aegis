# Working on this repository

This repository develops a portable workflow Skill, not a model runtime.
Read `skills/aegis/SKILL.md` and the architecture decision.
Keep coordination deterministic, stdlib-only, and accessible through `gh`.
Preserve host neutrality and progressive disclosure. Do not equate labels/comments with locks.
Run `python3 -m unittest discover -s tests -v` for coordination changes.
Do not mutate a live GitHub project to test without an explicitly authorized destination.
Document offline versus remote proof separately. Do not invent a GitHub URL or publication.
