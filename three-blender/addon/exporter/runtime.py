import bpy

from .context import DRACO_DECODER_PATH, POSTPROCESSING_VERSION, THREE_VERSION

TONE_MAPPING_BY_VIEW_TRANSFORM = {
    "Standard": "THREE.NoToneMapping",
    "Filmic": "THREE.ACESFilmicToneMapping",
    "AgX": "THREE.AgXToneMapping",
    "Khronos PBR Neutral": "THREE.NeutralToneMapping",
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Three.js Blender Scene</title>
  <!-- Your exported Blender scene lives in script.js; models and textures sit next to this file -->
  <style>
    body { margin: 0; overflow: hidden; }
    canvas { display: block; }
  </style>
  <script type="importmap">
    {
      "imports": {
        "three": "https://cdn.jsdelivr.net/npm/three@{version}/build/three.module.js",
        "three/addons/": "https://cdn.jsdelivr.net/npm/three@{version}/examples/jsm/"{postprocessing}
      }
    }
  </script>
</head>
<body>
  <script type="module" src="script.js"></script>
</body>
</html>
"""


def render_html(post_processing: bool = False) -> str:
    postprocessing_entry = ""
    if post_processing:
        postprocessing_entry = (
            ",\n"
            f'        "postprocessing": '
            f'"https://cdn.jsdelivr.net/npm/postprocessing@{POSTPROCESSING_VERSION}/build/index.js"'
        )
    return HTML_TEMPLATE.replace("{version}", THREE_VERSION).replace("{postprocessing}", postprocessing_entry)


class RuntimeGenerator:
    def __init__(self, scene, state, active_camera):
        self._scene = scene
        self._state = state
        self._active_camera = active_camera

    def assemble(self, sections: dict) -> str:
        parts = [
            self._imports(),
            self._rect_area_init(),
            self._renderer(),
            self._loader(),
            "const scene = new THREE.Scene();",
            self._mixers(),
            sections["world"],
            sections["cameras"] or self._fallback_camera(),
            sections["lights"],
            sections["objects"],
            sections["animations"],
            sections["postfx"],
            self._controls(),
            self._resize(),
            self._animate(),
        ]
        return "\n\n".join(part.strip() for part in parts if part)

    def _mixers(self) -> str:
        if not (self._state.has_meshes or self._state.has_object_animations):
            return ""
        return (
            "// Every animated thing plays through these mixers, updated once per frame\n"
            "const mixers = [];"
        )

    def _imports(self) -> str:
        lines = [
            "import * as THREE from 'three';",
            "import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';",
        ]
        if not self._state.active_camera_animated:
            lines.insert(1, "import { OrbitControls } from 'three/addons/controls/OrbitControls.js';")
        if self._state.use_draco:
            lines.append("import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';")
        if self._state.env_texture_url and not self._state.env_is_exr:
            lines.append("import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';")
        elif self._state.env_texture_url:
            lines.append("import { EXRLoader } from 'three/addons/loaders/EXRLoader.js';")
        if self._state.rect_area:
            lines.append("import { RectAreaLightUniformsLib } from 'three/addons/lights/RectAreaLightUniformsLib.js';")
        if self._state.post_processing:
            lines.append(self._postprocessing_import())
        return "\n".join(lines)

    def _postprocessing_import(self) -> str:
        names = ["EffectComposer", "RenderPass", "EffectPass", "SMAAEffect", "SMAAPreset"]
        if self._state.fx_bloom:
            names.append("BloomEffect")
        if self._state.fx_dof:
            names.append("DepthOfFieldEffect")
        if self._state.fx_tone_mapping:
            names.extend(["ToneMappingEffect", "ToneMappingMode"])
        return f"import {{ {', '.join(names)} }} from 'postprocessing';"

    def _rect_area_init(self) -> str:
        if not self._state.rect_area:
            return ""
        return (
            "// Required once so rectangular lights render correctly\n"
            "RectAreaLightUniformsLib.init();"
        )

    def _renderer(self) -> str:
        tone_mapping = TONE_MAPPING_BY_VIEW_TRANSFORM.get(
            self._scene.view_settings.view_transform, "THREE.NoToneMapping"
        )
        if self._state.post_processing:
            tone_mapping = "THREE.NoToneMapping"
        exposure = 2.0 ** self._scene.view_settings.exposure
        antialias = "false" if self._state.post_processing else "true"
        lines = [
            "// Renderer tuned to match Blender's color management (view transform and exposure)",
            "// Antialiasing is skipped when the post-processing chain supplies SMAA instead",
            (
                "const renderer = new THREE.WebGLRenderer({ "
                f"antialias: {antialias}, powerPreference: 'high-performance', stencil: false }});"
            ),
            "renderer.setSize(window.innerWidth, window.innerHeight);",
            "renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));",
            f"renderer.toneMapping = {tone_mapping};",
            f"renderer.toneMappingExposure = {exposure:.6f};",
        ]
        if self._state.post_processing:
            lines.insert(1, "// Tone mapping is handled inside the post-processing chain instead")
        if self._state.shadow_lights or self._state.has_meshes:
            lines.extend(
                [
                    "// Shadows enabled because the Blender scene uses shadow-casting lights",
                    "renderer.shadowMap.enabled = true;",
                    "renderer.shadowMap.type = THREE.PCFShadowMap;",
                ]
            )
        lines.append("document.body.appendChild(renderer.domElement);")
        return "\n".join(lines)

    def _loader(self) -> str:
        lines = [
            "// GLB loader shared by every exported mesh",
            "const loader = new GLTFLoader();",
        ]
        if self._state.use_draco:
            lines.extend(
                [
                    "",
                    "// Draco decoding for the compressed GLBs",
                    "const draco = new DRACOLoader();",
                    f"draco.setDecoderPath('{DRACO_DECODER_PATH}');",
                    "loader.setDRACOLoader(draco);",
                ]
            )
        return "\n".join(lines)

    def _fallback_camera(self) -> str:
        return (
            "// Fallback camera because the Blender scene has none\n"
            "const fallbackCamera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000.0);\n"
            "fallbackCamera.position.set(7.36, 4.96, 6.93);\n"
            "scene.add(fallbackCamera);\n"
            "const activeCamera = fallbackCamera;"
        )

    def _controls(self) -> str:
        if self._state.active_camera_animated:
            return (
                "// The Blender camera directs the shot, so manual orbiting is disabled for it"
            )
        return (
            "// Orbit to explore the exported scene, damped like the Blender viewport\n"
            "const controls = new OrbitControls(activeCamera, renderer.domElement);\n"
            "controls.enableDamping = true;\n"
            "controls.dampingFactor = 0.05;"
        )

    def _resize(self) -> str:
        body = self._resize_body()
        composer_resize = ""
        if self._state.post_processing:
            composer_resize = "\n  composer.setSize(window.innerWidth, window.innerHeight);"
        return (
            "// Keep framing and resolution in sync with the browser window\n"
            "window.addEventListener('resize', () => {\n"
            + body +
            composer_resize +
            "\n});"
        )

    def _resize_body(self) -> str:
        aspect = "window.innerWidth / window.innerHeight"
        if self._active_camera is None or self._active_camera[1] != "ORTHO":
            return (
                f"  const aspect = {aspect};\n"
                "  activeCamera.aspect = aspect;\n"
                "  activeCamera.updateProjectionMatrix();\n"
                "  renderer.setSize(window.innerWidth, window.innerHeight);"
            )
        half_view = f"{self._active_camera[0]}HalfView"
        return (
            f"  const half = {half_view};\n"
            f"  const aspect = {aspect};\n"
            "  const wide = aspect >= 1;\n"
            "  activeCamera.left = -(wide ? half : half * aspect);\n"
            "  activeCamera.right = wide ? half : half * aspect;\n"
            "  activeCamera.top = wide ? half / aspect : half;\n"
            "  activeCamera.bottom = -(wide ? half / aspect : half);\n"
            "  activeCamera.updateProjectionMatrix();\n"
            "  renderer.setSize(window.innerWidth, window.innerHeight);"
        )

    def _animate(self) -> str:
        needs_timer = self._state.has_meshes or self._state.has_object_animations
        mixer_update = "  mixers.forEach((mixer) => mixer.update(delta));\n" if needs_timer else ""
        timer_line = "const timer = new THREE.Timer();\n" if needs_timer else ""
        delta_line = "  timer.update();\n  const delta = timer.getDelta();\n" if needs_timer else ""
        controls_update = "  controls.update();\n" if not self._state.active_camera_animated else ""
        render_call = "renderer.render(scene, activeCamera);"
        if self._state.post_processing:
            render_call = "composer.render(delta);" if needs_timer else "composer.render();"
        return (
            "// Render loop: animations advance with real time, damping stays smooth\n"
            f"{timer_line}"
            "function animate() {\n"
            "  requestAnimationFrame(animate);\n"
            f"{delta_line}"
            f"{mixer_update}"
            f"{controls_update}"
            f"  {render_call}\n"
            "}\n"
            "animate();"
        )
