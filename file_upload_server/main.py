from fastapi import FastAPI, HTTPException, File, Form, UploadFile

app = FastAPI(title="Movie Upload API", version="1.0.0")

@app.post("/upload-movie")
async def upload_movie(file: UploadFile = File(...), meta: str = Form(...)):
    try:
        # 바이너리 데이터 읽기
        movie_binary = await file.read()
        
        # 여기서 영상 파일 저장 또는 처리 로직 구현
        with open("uploaded_movie.zip", "wb") as f:
                f.write(movie_binary)
        
        return {
            "status": "success",
            "message": "Movie uploaded successfully",
            "filename": file.filename,
            "meta_info": meta,
            "file_size": len(movie_binary)
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process movie: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Movie Upload API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
