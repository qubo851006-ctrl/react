@echo off
echo 正在安装 Python 依赖...
pushd %~dp0backend
pip install -r requirements.txt -q

echo 启动服务（端口 8000）...
echo 其他用户访问地址：http://[本机IP]:8000
uvicorn main:app --host 0.0.0.0 --port 8000
popd
pause
