@echo off
setlocal

:: Set the YouTube video URL
set "VIDEO_URL=https://www.youtube.com/watch?v=LjkLFhVD3rM"

:: Use yt-dlp to get the video title
for /f "delims=" %%i in ('yt-dlp --get-title --no-warnings "%VIDEO_URL%"') do set "TITLE=%%i"

:: Print the video title
echo Video Title: %TITLE%

endlocal
