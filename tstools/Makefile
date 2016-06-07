#/***************************************************************************
# TSTools
#
# Plugin for visualization and analysis of remote sensing time series
#                             -------------------
#        begin                : 2013-10-01
#        copyright            : (C) 2013 by Chris Holden
#        email                : ceholden@gmail.com
# ***************************************************************************/
#
#/***************************************************************************
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# ***************************************************************************/

# INSTALL LOCATION
LOC=$(HOME)/.qgis2/python/plugins

# CONFIGURATION
PLUGIN_UPLOAD = $(CURDIR)/plugin_upload.py

# LICENSE
LICENSE = $(CURDIR)/../LICENSE.txt

# Makefile for a PyQGIS plugin
# translation
SOURCES = src/*.py
#TRANSLATIONS = i18n/tstools_en.ts
TRANSLATIONS =

# global
PLUGINNAME = tstools

PY_FILES = src/*.py src/controls src/plots src/ts_driver src/utils

EXTRAS = media/ metadata.txt

UI_FILES = $(shell find ui/ -name 'ui*.ui' | sed 's|\.ui|\.py|g')

RESOURCE_FILES = resources_rc.py

default: compile

compile: $(UI_FILES) $(RESOURCE_FILES)

%_rc.py : %.qrc
	pyrcc4 -o $*_rc.py  $<

%.py : %.ui
	pyuic4 -o $@ $<

%.qm : %.ts
	lrelease $<

# The deploy  target only works on unix like operating system where
# the Python plugin directory is located at:
# $HOME/.qgis/python/plugins
deploy: compile transcompile
	mkdir -p $(LOC)/$(PLUGINNAME)
	cp -vRf $(PY_FILES) $(LOC)/$(PLUGINNAME)
	cp -vf $(UI_FILES) $(LOC)/$(PLUGINNAME)
	cp -vf $(RESOURCE_FILES) $(LOC)/$(PLUGINNAME)
	cp -vRf $(EXTRAS) $(LOC)/$(PLUGINNAME)
	cp -vfr i18n $(LOC)/$(PLUGINNAME)
	cp -vf $(LICENSE) $(LOC)/$(PLUGINNAME)

# The dclean target removes compiled python files from plugin directory
# also delets any .svn entry
dclean:
	find $(LOC)/$(PLUGINNAME) -iname "*.pyc" -delete
	find $(LOC)/$(PLUGINNAME) -iname ".svn" -prune -exec rm -Rf {} \;

# The derase deletes deployed plugin
derase:
	rm -Rf $(LOC)/$(PLUGINNAME)

# The zip target deploys the plugin and creates a zip file with the deployed
# content. You can then upload the zip file on http://plugins.qgis.org
zip: deploy dclean
	rm -f ../$(PLUGINNAME).zip
	cd $(LOC); zip -9r $(CURDIR)/../$(PLUGINNAME).zip $(PLUGINNAME)

# Create a zip package of the plugin named $(PLUGINNAME).zip.
# This requires use of git (your plugin development directory must be a
# git repository).
# To use, pass a valid commit or tag as follows:
#   make package VERSION=Version_0.3.2
package: compile
		rm -f $(PLUGINNAME).zip
		git archive --prefix=$(PLUGINNAME)/ -o $(PLUGINNAME).zip $(VERSION)
		echo "Created package: $(PLUGINNAME).zip"

upload: zip
	$(PLUGIN_UPLOAD) $(PLUGINNAME).zip

# transup
# update .ts translation files
transup:
	pylupdate4 Makefile

# transcompile
# compile translation files into .qm binary format
transcompile: $(TRANSLATIONS:.ts=.qm)

# transclean
# deletes all .qm files
transclean:
	rm -f i18n/*.qm

clean:
	rm $(UI_FILES) $(RESOURCE_FILES)
