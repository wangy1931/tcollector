@echo off
set allparam=
:param
set str=%1
if "%str%"=="" (
    goto end
)
if "%allparam%"=="" (
set allparam=%str%
) else (
set allparam=%allparam% %str%
)
shift /0
goto param
:end
powershell -f /opt/cloudwiz-agent/altenv/bin/supervisor1.ps1 %allparam%