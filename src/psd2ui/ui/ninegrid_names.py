"""Project-wide name exclusions shared by exporting and manual inspection."""
from pathlib import Path
import tomllib

from ninegrid.names import DEFAULT_IGNORE_NAMES, normalize_ignored_names, matches_ignored_name


def configured_ignore_names(config=None):
    from .environment import project_config
    chosen=config if config is not None else project_config()
    if chosen is None:return DEFAULT_IGNORE_NAMES
    path=Path(chosen)
    if not path.exists():return DEFAULT_IGNORE_NAMES
    with path.open('rb') as file:data=tomllib.load(file)
    options=data.get('export',{})
    if not isinstance(options,dict):raise ValueError('配置 [export] 必须是表')
    return normalize_ignored_names(options.get('ninegrid_ignore_names',DEFAULT_IGNORE_NAMES))
