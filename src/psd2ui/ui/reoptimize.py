"""Native engine resize bridge used by PSD export's final verification only."""
from .environment import playwright_module

def validate_resizing(stage,images,project,**options):
    from ninegrid.laya.resize import validate_resizing as library_validate_resizing
    from ninegrid.laya.runtime import engine_options
    with engine_options(playwright_module=playwright_module()):
        return library_validate_resizing(stage,images/'export-records/ninegrid',project,**options)
