import bpy

from .animation import TransformAnimator
from .cameras import CameraExporter
from .context import ExportPaths, ExportState, THREE_VERSION
from .lights import LightExporter
from .objects import ObjectExporter
from .postfx import PostFXExporter
from .runtime import RuntimeGenerator, render_html
from .world import WorldExporter


class SceneExporter:
    def __init__(self, html_path: str, scene=None):
        self._paths = ExportPaths.from_html_path(html_path)
        self._scene = scene or bpy.context.scene
        self._state = ExportState(paths=self._paths)
        self._state.post_processing = bool(getattr(self._scene, "threejs_use_postprocessing", False))

    def run(self):
        bpy.context.view_layer.update()
        self._paths.prepare()
        sections = self._collect_sections()
        generator = RuntimeGenerator(self._scene, self._state, sections.pop("_active_camera"))
        js_content = generator.assemble(sections)
        self._paths.js_file.write_text(js_content, encoding="utf-8")
        self._paths.html_file.write_text(render_html(self._state.post_processing), encoding="utf-8")
        return self._paths.html_file

    def _collect_sections(self) -> dict:
        cameras = CameraExporter(self._state)
        camera_section = cameras.generate()
        world_section = WorldExporter(self._state).generate()
        lights_section = LightExporter(self._state).generate()
        objects_section = ObjectExporter(self._state).generate()
        animator = TransformAnimator(self._state, cameras.active_object)
        animation_section = animator.generate()
        postfx = PostFXExporter(self._state, cameras.active_object, self._scene)
        return {
            "cameras": camera_section,
            "world": world_section,
            "lights": lights_section,
            "objects": objects_section,
            "animations": animation_section,
            "postfx": postfx.generate(),
            "_active_camera": cameras.active,
        }
