@echo off
mkdir logs
echo "" >> logs\collector.log
mkdir runs
echo "" >> runs\collector.pid
rd /s /q build
rd /s /q dist
python win_setup.py bdist_msi
rd /s /q deploy\releases\windows\dist
move  dist deploy\releases\windows
rd /s /q build
rd /s /q dist
rd /s /q logs
rd /s /q runs