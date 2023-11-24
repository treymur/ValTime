

# to get image from url:
import urllib.request
from io import BytesIO
from PIL import Image, ImageTk

def url_to_ImageTk(url, width=None, height=None) -> ImageTk.PhotoImage:
    try:
        response = urllib.request.urlopen(url)
        image = Image.open(BytesIO(response.read()))
    except Exception as e:
        raise ImageFetchError(f"Failed to fetch image from {url}") from e
    response.close()
    if width is not None and height is not None:
        image = image.resize((width, height), Image.LANCZOS)
    photo = ImageTk.PhotoImage(image)
    return photo


class ImageFetchError(Exception):
    """Raised when fetching an image from a URL fails."""
    pass