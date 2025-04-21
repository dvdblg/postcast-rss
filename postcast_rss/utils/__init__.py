import html


def unescape(text):
    """
    Unescapes HTML entities in the given text.

    Args:
        text (str or None): The text to unescape. If None, the function returns None.

    Returns:
        str or None: The unescaped text, or None if the input is None.
    """
    if text is None:
        return None
    return html.unescape(text)


def build_url(*parts):
    """
    Constructs a URL by joining multiple parts with a forward slash ('/').

    Args:
        *parts: A variable number of string or other objects representing parts of the URL.
                Each part will be stripped of leading and trailing slashes before joining.

    Returns:
        str: The constructed URL as a single string.

    Example:
        build_url("http://example.com", "path", "/to/resource/")
        # Returns: "http://example.com/path/to/resource"
    """
    return "/".join(str(part).strip("/") for part in parts if part is not None)
