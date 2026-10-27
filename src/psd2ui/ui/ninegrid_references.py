"""Project-owned decoration allowlist around NineGrid's official native policy."""
from ninegrid.laya.native import geometry_relations,references as native_references
from ninegrid.laya.policy import native_ui_policy
from .list_layout import DECORATION_UUID

def references(project):return native_references(project,(DECORATION_UUID,))
def native_ui_references():return native_ui_policy((DECORATION_UUID,))
