"""PSD export orchestration around the installed NineGrid public API."""
from pathlib import Path
import json,shutil
from ninegrid.api import optimize_project
from ninegrid.laya.runtime import verified_engine as project_version,engine_options
from ninegrid.laya.validation import validate_engine as library_validate_engine
from .list_layout import DECORATION_UUID
from .ninegrid_names import configured_ignore_names,normalize_ignored_names

from .environment import playwright_module

def optimize(stage_project,staged,original_project,mode,workers,engine_dir,ignore_names=None):
    ignore_names=configured_ignore_names() if ignore_names is None else normalize_ignored_names(ignore_names)
    records=staged/'export-records/ninegrid'
    try:
        return optimize_project(stage_project,staged,original_project=original_project,
            records_directory=records,mode=mode,workers=workers,engine_dir=engine_dir,
            ignore_names=ignore_names,allowed_component_types=(DECORATION_UUID,),playwright_module=playwright_module())
    except BaseException as error:
        # The surrounding PSD transaction owns final publication and diagnostics.
        failure=stage_project.parent.parent/'failures'/stage_project.name
        failure.mkdir(parents=True,exist_ok=True)
        if records.exists():shutil.copytree(records,failure/'records',dirs_exist_ok=True)
        (failure/'failure.json').write_text(json.dumps({'error':str(error)},indent=2)+'\n')
        raise

def validate_engine(*args,**kwargs):
    with engine_options(playwright_module=playwright_module()):return library_validate_engine(*args,**kwargs)
