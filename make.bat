pyinstaller %1 %2 %3 %4 %5 -yw -i "leacto.ico" -p "Lib/site-packages" --add-data "leacto.ico:." --add-data "leacto.ui:." --add-data "leacto_browser.ui:." -n Leacto leacto.py
