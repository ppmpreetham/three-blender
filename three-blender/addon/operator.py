import bpy
from bpy.types import Operator

from .exporter import SceneExporter


class THREEJS_OT_export_scene(Operator):
    bl_idname = "threejs.export_scene"
    bl_label = "Export Three.js Scene"
    bl_description = "Write an HTML page plus models, textures and script.js next to it"
    bl_options = {"REGISTER"}

    def execute(self, context):
        html_path = context.scene.threejs_html_path
        if not html_path:
            self.report({"ERROR"}, "Specify an HTML file path first")
            context.scene.threejs_export_status = "ERROR: no HTML path set"
            return {"CANCELLED"}
        try:
            output = SceneExporter(html_path, scene=context.scene).run()
        except Exception as exc:
            context.scene.threejs_export_status = f"ERROR: {exc}"
            self.report({"ERROR"}, f"Export failed: {exc}")
            return {"CANCELLED"}
        status = f"Exported: {output}"
        context.scene.threejs_export_status = status
        self.report({"INFO"}, status)
        return {"FINISHED"}


def register():
    bpy.utils.register_class(THREEJS_OT_export_scene)


def unregister():
    bpy.utils.unregister_class(THREEJS_OT_export_scene)
