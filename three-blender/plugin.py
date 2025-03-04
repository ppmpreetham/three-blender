bl_info = {
    "name": "Three-Blender",
    "author": "Preetham Pemmasani",
    "version": (1, 0),
    "blender": (2, 93, 0),
    "location": "Output Properties > Three.js Export",
    "description": "Integrates your Blender scenes with Three.JS",
    "category": "Import-Export",
    "tracker_url": "https://github.com/ppmpreetham/three-blender/issues",
}

import bpy
import os
from bpy.props import StringProperty
from bpy.types import Panel, Operator
from mathutils import Vector

class THREEJS_PT_export_panel(Panel):
    bl_label = "Three.js Export"
    bl_idname = "THREEJS_PT_export_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.label(text="Export Scene to Three.js:")
        layout.prop(scene, "threejs_html_path", text="HTML File Path")
        
        row = layout.row()
        row.operator("threejs.export_scene", text="Export Scene")
        
        # Status message
        if hasattr(scene, "threejs_export_status") and scene.threejs_export_status:
            box = layout.box()
            box.label(text=scene.threejs_export_status)

class THREEJS_OT_export_scene(Operator):
    bl_idname = "threejs.export_scene"
    bl_label = "Export Three.js Scene"
    bl_description = "Export the current scene to Three.js format"
    
    def execute(self, context):
        html_path = context.scene.threejs_html_path
        
        if not html_path:
            self.report({'ERROR'}, "Please specify an HTML file path")
            context.scene.threejs_export_status = "ERROR: No HTML file path specified"
            return {'CANCELLED'}
        
        # export directory
        html_dir = os.path.dirname(html_path)
        
        if not os.path.exists(html_dir):
            try:
                os.makedirs(html_dir, exist_ok=True)
            except:
                self.report({'ERROR'}, f"Could not create directory: {html_dir}")
                context.scene.threejs_export_status = f"ERROR: Could not create directory: {html_dir}"
                return {'CANCELLED'}
        
        # exported_gltfs folder
        export_dir = os.path.join(html_dir, "exported_gltfs")
        try:
            os.makedirs(export_dir, exist_ok=True)
        except:
            self.report({'ERROR'}, f"Could not create directory: {export_dir}")
            context.scene.threejs_export_status = f"ERROR: Could not create directory: {export_dir}"
            return {'CANCELLED'}
        
        try:
            # Generate JavaScript and HTML files
            self.export_threejs(html_path, export_dir)
            context.scene.threejs_export_status = f"Successfully exported to: {html_path}"
            self.report({'INFO'}, f"Successfully exported to: {html_path}")
        except Exception as e:
            import traceback
            self.report({'ERROR'}, f"Export error: {str(e)}")
            context.scene.threejs_export_status = f"ERROR: {str(e)}"
            print(traceback.format_exc())
            return {'CANCELLED'}
            
        return {'FINISHED'}
    
    def safe_name(self, name: str):
        ACCENT_MAP = {
        "á": "a", "à": "a", "ã": "a", "â": "a", "ä": "ae", "å": "a",
        "č": "c", "ć": "c", 
        "é": "e", "è": "e", "ê": "e", "ë": "e", 
        "í": "i", "ì": "i", "î": "i", "ï": "i",
        "ñ": "n",
        "ó": "o", "ò": "o", "ô": "o", "ö": "oe", "õ": "o", "ø": "o",
        "ř": "r",
        "š": "s", "ß": "ss",
        "ú": "u", "ù": "u", "û": "u", "ü": "ue", "ũ": "u",
        "ý": "y", "ž": "z"
        }
        
        for accented, plain in ACCENT_MAP.items():
            name = name.replace(accented, plain)
            name = name.replace(accented.upper(), plain.upper())
        name = (
            name.replace(" ", "_")
                .replace("-", "_")
                .replace(".", "_")
        )
        return name
    
    def safe_transform(self, transform):
        return f"{transform.x}, {transform.z}, {-transform.y}"
    
    def bpy_color_to_hex(self, bpy_color):
        rgb = tuple(int(channel * 255) for channel in bpy_color)
        return '0x{:02x}{:02x}{:02x}'.format(*rgb)
    
    def addobjprop(self, object):
        location = object.location
        rotation = object.rotation_euler
        code = f"{self.safe_name(object.name)}.position.set({self.safe_transform(location)});\n"
        code += f"{self.safe_name(object.name)}.rotation.set({self.safe_transform(rotation)});\n"
        return code
    
    def export_obj(self, obj, export_dir):
        bpy.ops.object.select_all(action='DESELECT')

        if obj.type == "MESH":
            obj.select_set(True)
            export_path = os.path.join(export_dir, f"{self.safe_name(obj.name)}.gltf")
            bpy.ops.export_scene.gltf(filepath=export_path, use_selection=True)
            obj.select_set(False)
            return export_path
        return None
    
    def generate_html(self, html_path, js_path):
        # Create a basic HTML file that imports the script.js file
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Three.js Blender Scene</title>
    <style>
        body { margin: 0; overflow: hidden; }
        canvas { display: block; }
    </style>
</head>
<body>
    <!-- Import the three.js script -->
    <script type="module" src="script.js"></script>
</body>
</html>
"""
        
        with open(html_path, "w") as file:
            file.write(html_content)
    
    def loader(self, object):
        location = object.location
        rotation = object.rotation_euler
        obj_name = self.safe_name(object.name)

        load_code = f"loader.load('exported_gltfs/{obj_name}.glb',\n"
        load_code += "\t(gltf) => {\n"
        load_code += f"\t\tconst {obj_name} = gltf.scene;\n"
        load_code += f"\t\t{obj_name}.position.set({self.safe_transform(location)});\n"
        load_code += f"\t\t{obj_name}.rotation.set({self.safe_transform(rotation)});\n"
        load_code += f"\t\tscene.add({obj_name});\n"
        load_code += "\t},\n"
        load_code += "\t(xhr) => {\n"
        load_code += f"\t\tconsole.log('{obj_name} loaded: ' + (xhr.loaded / xhr.total * 100) + '%');\n"
        load_code += "\t},\n"
        load_code += "\t(error) => {\n"
        load_code += f"\t\tconsole.error('An error happened loading the model {obj_name}', error);\n"
        load_code += "\t}\n"
        load_code += ");\n"
        return load_code
    
    def export_threejs(self, html_path, export_dir):
        # Imports for Three.js
        imports = 'import * as THREE from "https://cdn.skypack.dev/three@0.129.0/build/three.module.js";\n'
        imports += 'import { OrbitControls } from "https://cdn.skypack.dev/three@0.129.0/examples/jsm/controls/OrbitControls.js";\n'
        imports += 'import { GLTFLoader } from "https://cdn.skypack.dev/three@0.129.0/examples/jsm/loaders/GLTFLoader.js";\n\n'
        
        # Scene initialization
        scene_init = "// Initialize the scene\n"
        scene_init += "const scene = new THREE.Scene();\n\n"
        
        # CAMERAS
        cam_code = "// CAMERAS\n"
        for camera in bpy.data.cameras:
            cam_name = self.safe_name(camera.name)
            cam_obj = bpy.data.objects.get(camera.name)
            if not cam_obj:
                continue
                
            cam_code += f"// {cam_name}\n"
            cam_code += f"const {cam_name} = new THREE.PerspectiveCamera({camera.lens}, window.innerWidth / window.innerHeight, 0.1, 1000);\n"
            cam_code += f"{cam_name}.position.set({self.safe_transform(cam_obj.location)});\n"
            cam_code += f"{cam_name}.rotation.set({self.safe_transform(cam_obj.rotation_euler)});\n"
            cam_code += f"console.log('Camera {cam_name} position:', {cam_name}.position);\n"
            cam_code += f"scene.add({cam_name});\n\n"
        
        # LIGHTS
        light_code = "// LIGHTS\n"
        for light in bpy.data.lights:
            light_name = self.safe_name(light.name)
            light_obj = bpy.data.objects.get(light.name)
            if not light_obj:
                continue
                
            try:
                # POINT LIGHT
                if light.type == "POINT":
                    light_code += f"const {light_name} = new THREE.PointLight({self.bpy_color_to_hex(light.color)});\n"
                    light_code += f"{light_name}.position.set({self.safe_transform(light_obj.location)});\n"

                # SPOT LIGHT
                elif light.type == "SPOT":
                    spot_size = light_obj.data.spot_size
                    light_code += f"const {light_name} = new THREE.SpotLight({self.bpy_color_to_hex(light.color)}, {light.energy}, {light.cutoff_distance}, {spot_size}, 0, 1);\n"
                    light_code += f"{light_name}.castShadow = true; // enable shadow\n"
                    
                    location = light_obj.location
                    
                    # Determining target location based on constraints
                    if light_obj.constraints:
                        for constraint in light_obj.constraints:
                            if constraint.type in {'TRACK_TO', 'DAMPED_TRACK', 'LOCKED_TRACK'} and constraint.target:
                                target_location = constraint.target.location
                                break
                    else:
                        # Calculate the target position if no constraint
                        target_location = location + light_obj.rotation_euler.to_matrix() @ Vector((0, 0, -1))
                    
                    light_code += f"{light_name}.target.position.set({self.safe_transform(target_location)});\n"

                # AREA LIGHT
                elif light.type == "AREA":
                    light_code += f"const {light_name} = new THREE.DirectionalLight({self.bpy_color_to_hex(light.color)}, {light.energy});\n"
                
                light_code += f"scene.add({light_name});\n\n"
            except Exception as e:
                print(f"Warning with light '{light.name}': {str(e)}")
                continue
        
        # OBJECTS
        obj_code = "// OBJECTS\n"
        
        # Check if GLTFLoader is needed
        has_meshes = any(obj.type == "MESH" for obj in bpy.data.objects)
        if has_meshes:
            obj_code += "const loader = new GLTFLoader();\n\n"
        
        for obj in bpy.data.objects:
            if obj.type == "MESH":
                obj_name = self.safe_name(obj.name)
                obj_code += f"// {obj_name}\n"
                filepath = self.export_obj(obj, export_dir)
                if filepath:
                    obj_code += self.loader(obj) + "\n"
        
        # RENDERER
        renderer_code = "// RENDERER\n"
        renderer_code += "const renderer = new THREE.WebGLRenderer();\n"
        renderer_code += "renderer.setSize(window.innerWidth, window.innerHeight);\n"
        renderer_code += "document.body.appendChild(renderer.domElement);\n"
        
        # Background color
        background_color = bpy.context.scene.world.color if hasattr(bpy.context.scene, 'world') and bpy.context.scene.world else (0, 0, 0)
        renderer_code += f"\n// Background Color\n"
        renderer_code += f"scene.background = new THREE.Color({self.bpy_color_to_hex(background_color)});\n"
        
        # Find a camera to use
        camera_used = None
        if bpy.data.cameras:
            for cam in bpy.data.cameras:
                if bpy.data.objects.get(cam.name):
                    camera_used = self.safe_name(cam.name)
                    break
        
        if not camera_used:
            # Add a default camera if none exists
            renderer_code += "\n// Default Camera (since no camera was found in the scene)\n"
            renderer_code += "const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);\n"
            renderer_code += "camera.position.set(0, 0, 5);\n"
            renderer_code += "scene.add(camera);\n"
            camera_used = "camera"
        
        # Event listeners
        renderer_code += "\n// Event Listeners\n"
        renderer_code += "window.addEventListener('resize', () => {\n"
        renderer_code += f"\t{camera_used}.aspect = window.innerWidth / window.innerHeight;\n"
        renderer_code += f"\t{camera_used}.updateProjectionMatrix();\n"
        renderer_code += "\trenderer.setSize(window.innerWidth, window.innerHeight);\n"
        renderer_code += "});\n"
        
        # Orbit Controls
        renderer_code += "\n// OrbitControls\n"
        renderer_code += f"const controls = new OrbitControls({camera_used}, renderer.domElement);\n"
        renderer_code += "controls.enableDamping = true;\n"
        renderer_code += "controls.dampingFactor = 0.05;\n"
        
        # Animation loop
        renderer_code += "\n// Animation loop\n"
        renderer_code += "function animate() {\n"
        renderer_code += "\trequestAnimationFrame(animate);\n"
        renderer_code += "\tcontrols.update(); // for damping\n"
        renderer_code += f"\trenderer.render(scene, {camera_used});\n"
        renderer_code += "}\n\n"
        renderer_code += "animate();\n"
        
        # Combine
                # Combine all code
        js_content = imports + scene_init + cam_code + light_code + obj_code + renderer_code
        
        # Save the JavaScript to a separate file
        js_path = os.path.join(os.path.dirname(html_path), "script.js")
        with open(js_path, "w") as file:
            file.write(js_content)
        
        # Generate and save the HTML file
        self.generate_html(html_path, js_path)
        
        # Also save three.js in the same folder as the HTML file
        three_js_path = os.path.join(os.path.dirname(html_path), "three.js")
        with open(three_js_path, "w") as file:
            file.write(js_content)
            
        return True

def register():
    bpy.types.Scene.threejs_html_path = StringProperty(
        name="HTML File Path",
        description="Path to save the exported HTML file",
        default="",
        subtype='FILE_PATH'
    )
    bpy.types.Scene.threejs_export_status = StringProperty(
        name="Export Status",
        default=""
    )
    
    bpy.utils.register_class(THREEJS_PT_export_panel)
    bpy.utils.register_class(THREEJS_OT_export_scene)

def unregister():
    bpy.utils.unregister_class(THREEJS_PT_export_panel)
    bpy.utils.unregister_class(THREEJS_OT_export_scene)
    
    del bpy.types.Scene.threejs_html_path
    del bpy.types.Scene.threejs_export_status

if __name__ == "__main__":
    register()