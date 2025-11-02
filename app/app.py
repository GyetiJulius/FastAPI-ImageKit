from fastapi import FastAPI, HTTPException, UploadFile, Form, Depends, File
from app.schemas import CreatePost
from app.db import Posts, get_async_session, create_db_and_tables
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.images import imagekit
import os
import shutil
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import uuid
import tempfile


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create database and tables
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

@app.post("/upload")
async def upload_post(
    file: UploadFile = File(...),
    caption: str = Form(""),
    session: AsyncSession = Depends(get_async_session),
):
    
    temp_file_path = None

    try:
        # Create a temporary file to store the uploaded content
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        # Upload the file to ImageKit
        upload_result = imagekit.upload_file(
            file=open(temp_file_path, "rb"),
            file_name=file.filename,
            options=UploadFileRequestOptions(
                use_unique_file_name=True,
                tags = ["posts"]
            )
        )

        # Check if upload was successful
        if upload_result.response_metadata.http_status_code == 200:
            post = Posts(
                    caption = caption,
                    url = upload_result.url,
                    file_type = "video" if file.content_type.startswith("video/") else "image",
                    file_name = upload_result.name
                )

            session.add(post)
            await session.commit()
            await session.refresh(post)
            return post
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally: 
        # Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()

@app.get("/feed")
async def get_feed(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Posts).order_by(Posts.created_at.desc()))
    posts = [row[0] for row in result.all()]

    post_data = []

    for post in posts:
        post_data.append({
            "id": str(post.id),
            "caption": post.caption,
            "url": post.url,
            "file_type": post.file_type,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat()
        })

    return {"posts": post_data}