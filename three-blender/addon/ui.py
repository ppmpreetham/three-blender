import bpy
from bpy.types import Panel


class THREEJS_PT_export_panel(Panel):
    bl_label = "Three.js Export"
    bl_idname = "THREEJS_PT_export_panel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="Export scene to a Three.js website:")
        layout.prop(scene, "threejs_html_path", text="HTML File")
        layout.prop(scene, "threejs_use_postprocessing", text="Post-Processing")
        layout.operator("threejs.export_scene", text="Export Scene", icon="EXPORT")
        if scene.threejs_export_status:
            box = layout.box()
            box.label(text=scene.threejs_export_status)


def register():
    bpy.utils.register_class(THREEJS_PT_export_panel)


def unregister():
    bpy.utils.unregister_class(THREEJS_PT_export_panel)
