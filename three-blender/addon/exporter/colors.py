def to_hex(color) -> str:
    channels = tuple(max(0, min(255, int(round(channel * 255)))) for channel in color[:3])
    return "0x{:02x}{:02x}{:02x}".format(*channels)
