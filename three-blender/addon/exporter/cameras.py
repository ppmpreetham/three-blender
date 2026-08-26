import math

import bpy

from .coords import position, quaternion

DEFAULT_FOCAL_LENGTH_MM = 50.0


def _sensor_size(camera) -> float:
    if camera.sensor_fit == "VERTICAL":
        return camera.sensor_height
    return camera.sensor_width


def _fov_degrees(camera) -> float:
    return math.degrees(2.0 * math.atan(_sensor_size(camera) / (2.0 * camera.lens)))


def _lens_label(camera) -> str:
    if camera.type == "ORTHO":
        return f"orthographic scale {camera.ortho_scale:g}"
    return f"{camera.lens:g}mm"


class CameraExporter:
    def __init__(self, state):
        self._state = state
        self.active = None
        self.active_object = None

    def generate(self) -> str:
        cameras = [obj for obj in bpy.data.objects if obj.type == "CAMERA"]
        if not cameras:
            return ""
        lines = ["// Cameras recreated from Blender camera objects"]
        for obj in cameras:
            lines.extend(self._camera_lines(obj))
        active = self._resolve_active(cameras)
        self.active_object = active
        self.active = (self._state.sanitizer.sanitize(active.name), active.data.type)
        lines.append(f"const activeCamera = {self.active[0]};")
        return "\n".join(lines) + "\n"

    def _resolve_active(self, cameras):
        scene_camera = bpy.context.scene.camera
        if scene_camera is not None and scene_camera.type == "CAMERA":
            return scene_camera
        return cameras[0]

    def _camera_lines(self, obj) -> list[str]:
        data = obj.data
        name = self._state.sanitizer.sanitize(obj.name)
        lines = [f"// {obj.name}: {_lens_label(data)}, clipping {data.clip_start:g} to {data.clip_end:g}"]
        lines.extend(self._constructor_lines(name, data))
        lines.append(f"{name}.position.set({position(obj.matrix_world.translation)});")
        lines.append(f"{name}.quaternion.set({quaternion(obj.matrix_world.to_3x3())});")
        lines.extend(self._shift_lines(name, data))
        lines.append(f"scene.add({name});")
        lines.append("")
        return lines

    def _constructor_lines(self, name: str, data) -> list[str]:
        near = f"{data.clip_start:.6f}"
        far = f"{data.clip_end:.6f}"
        if data.type == "ORTHO":
            half = f"{name}HalfView"
            aspect = "(window.innerWidth / window.innerHeight)"
            return [
                f"const {half} = {data.ortho_scale / 2.0:.6f};",
                (
                    f"const {name} = new THREE.OrthographicCamera(-{half}, {half}, "
                    f"{half} / {aspect}, -{half} / {aspect}, {near}, {far});"
                ),
            ]
        return [
            (
                f"const {name} = new THREE.PerspectiveCamera({_fov_degrees(data):.6f}, "
                f"window.innerWidth / window.innerHeight, {near}, {far});"
            )
        ]

    def _shift_lines(self, name: str, data) -> list[str]:
        if abs(data.shift_x) < 1e-6 and abs(data.shift_y) < 1e-6:
            return []
        offset_x = f"{-data.shift_x:.6f} * window.innerWidth"
        offset_y = f"{data.shift_y:.6f} * window.innerHeight"
        return [
            f"// Lens shift keeps the framing identical to the Blender camera",
            (
                f"{name}.setViewOffset(window.innerWidth, window.innerHeight, "
                f"{offset_x}, {offset_y}, window.innerWidth, window.innerHeight);"
            ),
        ]
