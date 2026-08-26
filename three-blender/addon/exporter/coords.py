from mathutils import Matrix, Vector

AXIS_CONVERSION = Matrix(((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)))


def _fmt(value: float) -> str:
    return f"{value + 0.0:.6f}"


def position(vector: Vector) -> str:
    return f"{_fmt(vector.x)}, {_fmt(vector.z)}, {_fmt(-vector.y)}"


def direction(vector: Vector) -> str:
    converted = AXIS_CONVERSION @ vector.normalized()
    return f"{_fmt(converted.x)}, {_fmt(converted.y)}, {_fmt(converted.z)}"


def quaternion(rotation_matrix: Matrix) -> str:
    gltf_space = AXIS_CONVERSION @ rotation_matrix @ AXIS_CONVERSION.inverted()
    q = gltf_space.to_quaternion()
    return f"{_fmt(q.x)}, {_fmt(q.y)}, {_fmt(q.z)}, {_fmt(q.w)}"
