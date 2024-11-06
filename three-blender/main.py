import bpy

def bpy_color_to_hex(bpy_color):
    rgb = tuple(int(channel * 255) for channel in bpy_color)
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

# CAMERAS

cam_code = ""

for i in bpy.data.cameras:
    print("\n")

    cam_loc = bpy.data.objects[i.name].location
    cam_rot = bpy.data.objects[i.name].rotation_euler
   
    print("CAMERA NAME: ", i.name)
    print("CAMERA LOCATION: ", cam_loc)
    print("CAMERA ROTATION: ", cam_rot)
    print("CAMERA TYPE: ", i.type)
    print("CAMERA LENS: ", i.lens)
    print("CAMERA SENSOR WIDTH: ", i.sensor_width)
    print("CAMERA SENSOR HEIGHT: ", i.sensor_height)
    print("CAMERA SENSOR FIT: ", i.sensor_fit)

    cam_code += f"const {i.name} = new THREE.PerspectiveCamera({i.lens}, window.innerWidth / window.innerHeight, 0.1, 1000);\n"
    cam_code += f"{i.name}.position.set({cam_loc.x}, {cam_loc.y}, {cam_loc.z});\n"
    cam_code += f"{i.name}.rotation.set({cam_rot.x}, {cam_rot.y}, {cam_rot.z});\n"

    print("\n")
    print(cam_code)

# LIGHTS

light_code = ""

for i in bpy.data.lights:

    print("\n")

    light_loc = bpy.data.objects[i.name].location
    light_rot = bpy.data.objects[i.name].rotation_euler

    print("LIGHT NAME: ", i.name)
    print("LIGHT LOCATION: ", light_loc)
    print("LIGHT ROTATION: ", light_rot)
    print("LIGHT TYPE: ", i.type)
    print("LIGHT COLOR: ", i.color)
    print("LIGHT ENERGY: ", i.energy)
    print("LIGHT POWER: ", i.power)