import uvicorn


def main():
    uvicorn.run(
        "gmail_mcp_server.app:app",  # import path to your `app`
        host="0.0.0.0",
        port=8000,
        reload=True,  # optional
    )


if __name__ == "__main__":
    main()
