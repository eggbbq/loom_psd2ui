"""Public component-UI export API. Uses psd-tools; never saves source files.

The legacy label-based API remains in psd2ui.exporter/psd2ui.cli. Use this
module for content/bg + normalized component naming, state/list contracts,
shared image recovery, native UI2 resources and transactional engine checks.
"""
from ..psd import PSDSource
from .layout import LayoutBuilder,page_roots
from .design_audit import inspect_design,DesignValidationError,check_source
from .exporter import discover,make_plans,export_feature
from .workflow import run_export
from .audit import audit
from .environment import export_environment,configure_defaults
from ..shared_images.pipeline import run as deduplicate_shared_images

__all__=['PSDSource','LayoutBuilder','page_roots','inspect_design','DesignValidationError',
         'check_source','discover','make_plans','export_feature','run_export','audit','export_environment',
         'configure_defaults','deduplicate_shared_images']
