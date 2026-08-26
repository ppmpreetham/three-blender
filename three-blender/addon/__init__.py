bl_info = {
    "name": "Three-Blender",
    "author": "Preetham Pemmasani",
    "version": (0, 2, 0),
    "blender": (4, 2, 0),
    "location": "Output Properties > Three.js Export",
    "description": "Compile Blender scenes into standalone Three.js websites",
    "category": "Import-Export",
    "tracker_url": "https://github.com/ppmpreetham/three-blender/issues",
}

from . import operator, properties, ui


def register():
    properties.register()
    ui.register()
    operator.register()


def unregister():
    operator.unregister()
    ui.unregister()
    properties.unregister()


if __name__ == "__main__":
    register()
