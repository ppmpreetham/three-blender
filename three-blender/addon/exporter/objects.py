import bpy

from .coords import position, quaternion

MODEL_RUNTIME = """// Model runtime: every unique Blender mesh is downloaded once.
// Linked duplicates of the same mesh become clones that share GPU buffers,
// and keyframed animations baked into the GLB start playing automatically.
const modelCache = new Map();
const placedModels = new Set();
const mixers = [];

function loadModel(url) {
  if (!modelCache.has(url)) {
    modelCache.set(url, new Promise((resolve, reject) => loader.load(url, resolve, undefined, reject)));
  }
  return modelCache.get(url);
}

async function placeModel(name, url, position, rotation) {
  try {
    const gltf = await loadModel(url);
    const isFirstInstance = !placedModels.has(url);
    const model = isFirstInstance ? gltf.scene : gltf.scene.clone(true);
    placedModels.add(url);
    model.name = name;
    model.position.set(position[0], position[1], position[2]);
    model.quaternion.set(rotation[0], rotation[1], rotation[2], rotation[3]);
    model.traverse((node) => {
      if (node.isMesh) {
        node.castShadow = true;
        node.receiveShadow = true;
      }
    });
    if (isFirstInstance && gltf.animations.length > 0) {
      const mixer = new THREE.AnimationMixer(model);
      gltf.animations.forEach((clip) => mixer.clipAction(clip).play());
      mixers.push(mixer);
    }
    scene.add(model);
  } catch (error) {
    console.error(`Failed to place model "${name}"`, error);
  }
}
"""


class ObjectExporter:
    def __init__(self, state):
        self._state = state
        self._url_by_mesh_data = {}

    def generate(self) -> str:
        meshes = [
            obj
            for obj in bpy.data.objects
            if obj.type == "MESH"
            and obj.data
            and not obj.hide_render
            and obj.visible_get()
        ]
        if not meshes:
            return ""
        self._state.has_meshes = True
        calls = []
        for obj in meshes:
            url = self._url_for(obj)
            calls.append(self._place_call(obj, url))
        return MODEL_RUNTIME + "\n".join(calls) + "\n"

    def _url_for(self, obj) -> str:
        key = obj.data.name
        if key not in self._url_by_mesh_data:
            self._url_by_mesh_data[key] = self._export_glb(obj)
        return self._url_by_mesh_data[key]

    def _export_glb(self, obj) -> str:
        file_name = f"{self._state.sanitizer.file_name(obj.data.name)}.glb"
        destination = self._state.paths.models_dir / file_name
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.export_scene.gltf(
            filepath=str(destination),
            use_selection=True,
            export_format="GLB",
            export_draco_mesh_compression_enable=self._state.use_draco,
        )
        return f"models/{file_name}"

    def _place_call(self, obj, url: str) -> str:
        name = self._state.sanitizer.sanitize(obj.name)
        world = obj.matrix_world
        return (
            f"// {obj.name}\n"
            f"placeModel('{name}', '{url}', [{position(world.translation)}], [{quaternion(world.to_3x3())}]);"
        )
