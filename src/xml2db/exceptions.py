class DataModelConfigError(Exception):
    """An exception to raise when model config provided by the user is erroneous"""

    pass


def check_type(src, key, exp_type, default):
    if exp_type.__name__ == "callable":
        if key in src and not callable(src[key]):
            raise DataModelConfigError(f"'{key}' must be callable")
    else:
        if key in src and not isinstance(src[key], exp_type):
            raise DataModelConfigError(f"'{key}' must be a {exp_type.__name__}")
    return src.get(key, default)
