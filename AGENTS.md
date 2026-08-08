# AGENTS.md

PySide6 + pyqtgraph desktop apps for OpendTect data, packaged with pixi (no pip/requirements.txt). Each app is a package under `src/` run via `pixi run`.

## Run

- `pixi run viewer` → `python src/slice_viewer`
- `pixi run zipmodel` → `python src/zipmodel_runner`
- Use the pixi env python (`.pixi/envs/default/bin/python`, currently 3.12; pixi.toml pins `<3.13`) — not a system python. All deps (PySide6, pyqtgraph, torch) live in the pixi env.

## Critical: external OpendTect deps

`odbind` and `dgbpy` are **not** pixi dependencies. They come from the OpendTect Pro install pointed to by `ODPYTHON` / `DGBPYTHON` in `[activation.env]` of `pixi.toml` — `${ODPYTHON}/bin/python` is prepended to `PYTHONPATH`. `pixi run` activates this env. If they're missing at runtime, `shared/uiodbind.py:odbind_found()` opens a file dialog to locate the install. Don't move these paths to pixi dependencies without checking with the maintainer. `zipmodel_runner` additionally requires an ODBind built from the OpendTect "main" branch.

## Import convention

`__main__.py` in each app does `sys.path.insert(0, <src>)`, then imports bare (`from ui.mainwindow import MainWindow`, `from shared.uiodbind import ...`). So modules are imported as `ui.*`, `shared.*`, `utils.*` — never `src.*` — and each app must be launched from its package root.

## Structure

- `src/slice_viewer/` — 3D seismic slice viewer (uses ODBind xarray accessors: `Seismic3D.iline/xline/zslice`).
- `src/zipmodel_runner/` — applies dGB ZipModels to seismic volumes; `utils/zipmodeltask.py` sets `Seismic3D.use_xarray = False` to use the numpy chunk API, then writes outputs via `outputvol.chunk[:] = ...`.
- `src/shared/` — reusable widgets both apps depend on: `uiodbind.py` (survey/volume/object selectors over ODBind), `uitools.py` (labelled combos, spinbox rows), `uiseisview.py` (pyqtgraph seismic view), `uijobqueue.py` (QThreadPool + progress table). Edit shared code with both apps' blast radius in mind.
- `src/marimo/scratch.py` — dev scratch notebook, not an app.

## Conventions

- Every source file starts with the GPLv3 copyright header — keep it on new files.
- No tests, linter, formatter, or CI config exist. Verification is manual: `pixi run viewer` / `pixi run zipmodel` (or `python -c "import ..."` under the pixi env).
- `pixi.lock` is generated (`linguist-generated`, `merge=binary` in `.gitattributes`). Never edit by hand; change `pixi.toml` and let pixi regenerate. Linux target pulls `pytorch-gpu` + CUDA 12; win-64 uses `pytorch-cpu`.
