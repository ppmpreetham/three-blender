import bpy

from .coords import AXIS_CONVERSION


class TransformAnimator:
    def __init__(self, state, active_camera=None):
        self._state = state
        self._active_camera = active_camera

    def generate(self) -> str:
        scene = bpy.context.scene
        start = scene.frame_start
        end = scene.frame_end
        if end <= start:
            return ""
        fps = max(scene.render.fps, 1)
        blocks = []
        for obj in self._bakeable_objects():
            js_name = self._state.sanitizer.sanitize(obj.name)
            block = self._block_for(obj, js_name, start, end, fps)
            if block:
                self._state.has_object_animations = True
                if obj is self._active_camera:
                    self._state.active_camera_animated = True
                blocks.append(block)
        return "\n".join(blocks) + "\n"

    @staticmethod
    def _bakeable_objects():
        return [obj for obj in bpy.data.objects if obj.type in {"CAMERA", "LIGHT"}]

    def _block_for(self, obj, js_name: str, start: int, end: int, fps: int) -> str:
        samples = self._sample(obj, start, end, fps)
        if not self._has_motion(samples):
            return ""
        times = [f"{time:.5f}" for time, _, _ in samples]
        positions = [f"{p[0]:.5f}, {p[1]:.5f}, {p[2]:.5f}" for _, p, _ in samples]
        quaternions = [f"{q[0]:.5f}, {q[1]:.5f}, {q[2]:.5f}, {q[3]:.5f}" for _, _, q in samples]
        duration = times[-1]
        return (
            f"// {obj.name} motion baked from Blender keyframes, constraints and drivers included\n"
            "{\n"
            f"  const clip = new THREE.AnimationClip('{js_name} Action', {duration}, [\n"
            f"    new THREE.VectorKeyframeTrack('.position', [{', '.join(times)}], [{', '.join(positions)}]),\n"
            f"    new THREE.QuaternionKeyframeTrack('.quaternion', [{', '.join(times)}], [{', '.join(quaternions)}]),\n"
            "  ]);\n"
            f"  const mixer = new THREE.AnimationMixer({js_name});\n"
            "  mixer.clipAction(clip).play();\n"
            "  mixers.push(mixer);\n"
            "}\n"
        )

    @staticmethod
    def _sample(obj, start: int, end: int, fps: int) -> list:
        samples = []
        original_frame = bpy.context.scene.frame_current
        try:
            for frame in range(start, end + 1):
                bpy.context.scene.frame_set(frame)
                bpy.context.view_layer.update()
                matrix = obj.matrix_world
                rotation = AXIS_CONVERSION @ matrix.to_3x3() @ AXIS_CONVERSION.inverted()
                quaternion = rotation.to_quaternion()
                translation = matrix.translation
                samples.append(
                    (
                        frame / fps,
                        (translation.x, translation.z, -translation.y),
                        (quaternion.x, quaternion.y, quaternion.z, quaternion.w),
                    )
                )
        finally:
            bpy.context.scene.frame_set(original_frame)
        return samples

    @staticmethod
    def _has_motion(samples: list) -> bool:
        if len(samples) < 2:
            return False
        first_time, first_position, first_quaternion = samples[0]
        for _, position, quaternion in samples[1:]:
            moved = any(abs(a - b) > 1e-6 for a, b in zip(position, first_position))
            dot = abs(sum(a * b for a, b in zip(quaternion, first_quaternion)))
            rotated = dot < 1.0 - 1e-6
            if moved or rotated:
                return True
        return False
