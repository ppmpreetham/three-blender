import bpy
from bpy.props import BoolProperty, StringProperty


def register():
    bpy.types.Scene.threejs_html_path = StringProperty(
        name="HTML File Path",
        description="Where the exported website is written",
        default="",
        subtype="FILE_PATH",
    )
    bpy.types.Scene.threejs_use_postprocessing = BoolProperty(
        name="Post-Processing",
        description="Add a pmndrs/postprocessing pipeline with bloom, depth of field and tone mapping taken from your scene",
        default=False,
    )
    bpy.types.Scene.threejs_export_status = StringProperty(
        name="Export Status",
        default="",
    )


def unregister():
    del bpy.types.Scene.threejs_html_path
    del bpy.types.Scene.threejs_use_postprocessing
    del bpy.types.Scene.threejs_export_status
