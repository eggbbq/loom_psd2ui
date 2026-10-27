"""Caller-owned workspace/configuration and optional browser dependency paths."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

_DEFAULTS={}
_CURRENT=ContextVar('psd2ui_export_environment',default={})

def configure_defaults(*,root=None,playwright_module=None,config_path=None):
    """Compatibility callers may explicitly set their own entrypoint defaults."""
    for key,value in dict(root=root,playwright_module=playwright_module,config_path=config_path).items():
        if value is not None:_DEFAULTS[key]=Path(value).resolve()

def workspace_root():return Path(_CURRENT.get().get('root',_DEFAULTS.get('root',Path.cwd()))).resolve()
def playwright_module():return _CURRENT.get().get('playwright_module',_DEFAULTS.get('playwright_module'))
def project_config():return _CURRENT.get().get('config_path',_DEFAULTS.get('config_path'))

@contextmanager
def export_environment(*,root=None,playwright_module=None,config_path=None):
    values=dict(_CURRENT.get())
    for key,value in dict(root=root,playwright_module=playwright_module,config_path=config_path).items():
        if value is not None:values[key]=Path(value).resolve()
    token=_CURRENT.set(values)
    try:yield
    finally:_CURRENT.reset(token)
