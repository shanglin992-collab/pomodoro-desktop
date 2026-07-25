@echo off
chcp 65001 >nul
echo ============================================
echo   🍅 番茄钟 - 打包为独立 EXE 文件
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python，请先安装 Python 3
    pause & exit /b 1
)

echo [1/3] 安装打包依赖...
pip install -r requirements.txt pyinstaller -q

echo [2/3] PyInstaller 打包中（约 30 秒）...
pyinstaller --noconsole --onefile --name "番茄钟" main.py 2>&1

if %errorlevel% neq 0 (
    echo ❌ 打包失败，请检查上面的错误信息
    pause & exit /b 1
)

echo [3/3] ✅ 完成！
echo.
echo 可执行文件位置: %~dp0dist\番茄钟.exe
echo.
echo 你可以把这个 exe 复制到桌面或任意位置直接双击运行。
echo.

:: Copy to project root for convenience
copy /y "%~dp0dist\番茄钟.exe" "%~dp0番茄钟.exe" >nul 2>&1
if %errorlevel% equ 0 (
    echo 已复制到项目根目录: %~dp0番茄钟.exe
)

pause
