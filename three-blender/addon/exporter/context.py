from dataclasses import dataclass, field
from pathlib import Path

from .naming import NameSanitizer

THREE_VERSION = "0.185.0"
POSTPROCESSING_VERSION = "6.39.4"
DRACO_DECODER_PATH = "https://www.gstatic.com/draco/versioned/decoders/1.5.7/"
MODELS_DIR = "models"
TEXTURES_DIR = "textures"


@dataclass
class ExportPaths:
    html_file: Path
    js_file: Path
    models_dir: Path
    textures_dir: Path

    @classmethod
    def from_html_path(cls, html_path: str) -> "ExportPaths":
        html = Path(html_path).resolve()
        root = html.parent
        return cls(
            html_file=html,
            js_file=root / "script.js",
            models_dir=root / MODELS_DIR,
            textures_dir=root / TEXTURES_DIR,
        )

    def prepare(self) -> None:
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.textures_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class ExportState:
    paths: ExportPaths
    sanitizer: NameSanitizer = field(default_factory=NameSanitizer)
    use_draco: bool = True
    rect_area: bool = False
    env_texture_url: str | None = None
    env_is_exr: bool = False
    shadow_lights: bool = False
    has_meshes: bool = False
    background_hex: str = "0x000000"
    post_processing: bool = False
    fx_bloom: bool = False
    fx_dof: bool = False
    fx_tone_mapping: bool = False
    has_object_animations: bool = False
    active_camera_animated: bool = False
