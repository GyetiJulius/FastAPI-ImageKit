from pydantic import BaseModel

class CreatePost(BaseModel):
    """
    Schema for creating a new post.
    Args:
        title (str): The title of the post.
        content (str): The content of the post.
    """
    title: str
    content: str