import uvicorn
from src.api.routes import app

if __name__ == "__main__":
    print("猫でもわかる技術解説エージェント - Webサーバー起動")
    uvicorn.run("src.api.routes:app", host="0.0.0.0", port=8000, reload=True)