@echo off
pushd D:\claude\react\backend
uvicorn main:app --reload --port 8000
popd
pause
