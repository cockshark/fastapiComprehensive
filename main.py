
from cgi import print_arguments


from fastapi import FastAPI, Request

app = FastAPI(
    servers=[
        {"url": "/", "description": "这是你自己哦"},
        {"url": "https://stag.example.com", "description": "Staging environment"},
        {"url": "https://prod.example.com", "description": "Production environment"},
    ],
    root_path="/api",
)


@app.get("/api/test")
def read_main(request: Request):

    return {"message": "Hello World", "root_path": request.scope.get("root_path")}
