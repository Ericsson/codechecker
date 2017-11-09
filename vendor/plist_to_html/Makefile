# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

CODEMIRROR = https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.30.0

BUILD_DIR = build
BIN_DIR = $(BUILD_DIR)/bin
DIST_DIR = $(BUILD_DIR)/dist

default: all

all: package

package: dep
	mkdir -p $(BIN_DIR)
	cp plist_to_html/dist/layout.html $(DIST_DIR)
	cp plist_to_html/dist/css/style.css $(DIST_DIR)
	cp plist_to_html/dist/js/bugviewer.js $(DIST_DIR)
	cp plist_to_html/PlistToHtml.py $(BIN_DIR)/plist-to-html

dist_dir:
	mkdir -p $(DIST_DIR)

dep: codemirror

codemirror: $(DIST_DIR)/codemirror.min.js
codemirror: $(DIST_DIR)/codemirror.min.css
codemirror: $(DIST_DIR)/codemirror.LICENSE
codemirror: $(DIST_DIR)/clike.min.js

$(DIST_DIR)/codemirror.min.js: dist_dir
	[ -f $(DIST_DIR)/codemirror.min.js ] && : || \
	curl -sSfLk --get $(CODEMIRROR)/codemirror.min.js \
			 -z $(DIST_DIR)/codemirror.min.js \
			 -o $(DIST_DIR)/codemirror.min.js

$(DIST_DIR)/codemirror.min.css: dist_dir
	[ -f $(DIST_DIR)/codemirror.min.css ] && : || \
	curl -sSfLk --get $(CODEMIRROR)/codemirror.min.css \
			 -z $(DIST_DIR)/codemirror.min.css \
			 -o $(DIST_DIR)/codemirror.min.css

$(DIST_DIR)/codemirror.LICENSE: dist_dir
	[ -f $(DIST_DIR)/codemirror.LICENSE ] && : || \
	curl -sSfLk --get https://raw.githubusercontent.com/codemirror/CodeMirror/master/LICENSE \
			 -z $(DIST_DIR)/codemirror.LICENSE \
			 -o $(DIST_DIR)/codemirror.LICENSE

$(DIST_DIR)/clike.min.js: dist_dir
	[ -f $(DIST_DIR)/clike.min.js ] && : || \
	curl -sSfLk --get $(CODEMIRROR)/mode/clike/clike.min.js \
			 -z $(DIST_DIR)/clike.min.js \
			 -o $(DIST_DIR)/clike.min.js

clean:
	rm -rf $(BUILD_DIR)
