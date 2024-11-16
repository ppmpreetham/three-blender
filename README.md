# three-blender
Write Zero lines of ThreeJS! Now compile your Blender scenes automatically into ThreeJS websites! 

Built with 💖 by [Preetham Pemmasani](https://github.com/ppmpreetham)

Preview
https://github.com/user-attachments/assets/29a39b08-c466-4277-9f95-1c2174b6ae69


## Usage
1. In your default html file, put this code snippet 
```html
<script type="module" src="three.js"></script>
```
2. Paste this script in blender's `Scripting` and hit run

3. The files (including the 3d models) would be saved in the same folder as the blend file.

4. Paste these files in your html folder and run the html file.

5. Voila! Your 3d scene will now be rendered in the browser.

## TODO:
- [ ] Fix the coordination system, rotation and position of meshes
- [ ] Add support for HDRi (by converting it to cubemaps)
- [ ] Support for more lights (Area light and Sun)
- [ ] Support for keyframes
- [ ] Apply modifier before exporting the model.
- [ ] Draco GLB compression selection by user
- [ ] Support for Volumetrics

## Limitations

- The coordinate system is broken due to differences between ThreeJS and Blender.

- Keyframes are not supported currently.

- The script only works for blender 4.0 and above.

## Contributing
1. Fork the repository.

2. Clone the repository.

3. Create a new branch.

4. Make changes and commit them.

5. Push the changes to your fork.

6. Create a pull request.

7. Make sure to follow the code of conduct.