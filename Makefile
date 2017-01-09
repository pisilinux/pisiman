all:
	py2uic5 -o gui/ui/main.py gui/ui/main.ui
	py2uic5 -o gui/ui/languages.py gui/ui/rawlanguages.ui
	py2uic5 -o gui/ui/packages.py gui/ui/packages.ui
	py2uic5 -o gui/ui/packagecollection.py gui/ui/packagecollection.ui
	py2rcc5 -o gui/ui/raw_rc.py gui/ui/raw.qrc

clean:
	find -name *.pyc | xargs rm -rf
	rm -rf gui/ui/main.py
	rm -rf gui/ui/languages.py
	rm -rf gui/ui/packages.py
	rm -rf gui/ui/packagecollections.py
	rm -rf gui/ui/raw_rc.py
