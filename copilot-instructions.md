# Copilot Instructions

Keep changes small and repo-specific.

## Project shape

- `controllers.py` wires the UI to the service layer through Qt signals and slots.
- `services.py` owns conversion, rename, PSARC handling, and worker-thread execution.
- `models.py` carries process settings into the service layer.
- `mainwindow.ui` is the source for the generated `mainwindow.py` file.

## Editing rules

- Import Qt objects through `rocksmithconvert.qt_wrapper` instead of importing `PyQt5` or `PyQt6` directly.
- Keep UI behavior in the window and controller layers. Keep file conversion behavior in `services.py`.
- Preserve the current worker pattern: background work emits progress and info through `_WorkerSignals`.
- Prefer focused fixes over refactors. Do not rewrite generated UI files by hand unless the task requires a targeted import fix.

## Tests and verification

- Use `pytest` for tests.
- Follow the existing style in `tests/test_gui_changes_reflect_on_model.py` for controller and widget behavior.
- When changing controller or settings behavior, prefer tests that assert the produced `ProcessModel` or emitted side effects.

## Documentation and maintenance

- Keep README changes short and practical.
- Avoid adding generic style-guide content that is not specific to this repo.
- If a change exposes a missing behavior or risky area, note it in `todo.md` instead of expanding scope during the same change.