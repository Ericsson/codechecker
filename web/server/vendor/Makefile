VENDOR_DIR = $(shell pwd)
BUILD_DIR = $(VENDOR_DIR)/build

# Git tag versions of external dependencies.
THRIFT_VERSION = 0.9.2
CODEMIRROR_VERSION = 5.25.0
JSPLUMB_VERSION = 2.2.0
MARKED_VERSION = v0.3.3

# Other external dependency versions.
JQUERY_VERSION = 3.4.1
DOJO_VERSION = 1.10.4
HIGHLIGHT_VERSION = 9.0.0

default: build

dep: $(VENDOR_DIR)/thrift
dep: $(VENDOR_DIR)/codemirror
dep: $(VENDOR_DIR)/codemirror/dist/codemirror.min.js
dep: $(VENDOR_DIR)/jsplumb
dep: $(VENDOR_DIR)/marked
dep: $(VENDOR_DIR)/jquery/jquery-$(JQUERY_VERSION)-min.js
dep: $(VENDOR_DIR)/dojotoolkit
dep: $(VENDOR_DIR)/highlightjs/highlight.min.js
dep: $(VENDOR_DIR)/highlightjs/css/xcode.min.css

vendor_dir:
	mkdir -p $(VENDOR_DIR)

# We download the whole thrift repository but we use only the thrift.js file.
$(VENDOR_DIR)/thrift: vendor_dir
	[ -d $(VENDOR_DIR)/thrift ] && : || \
	git clone --depth 1 --single-branch -b $(THRIFT_VERSION) \
		https://github.com/apache/thrift.git $(VENDOR_DIR)/thrift

$(VENDOR_DIR)/codemirror: vendor_dir
	[ -d $(VENDOR_DIR)/codemirror ] && : || \
	git clone --depth 1 --single-branch -b $(CODEMIRROR_VERSION) \
		https://github.com/codemirror/CodeMirror.git $(VENDOR_DIR)/codemirror

$(VENDOR_DIR)/codemirror/dist: $(VENDOR_DIR)/codemirror
	mkdir -p $(VENDOR_DIR)/codemirror/dist

$(VENDOR_DIR)/codemirror/dist/codemirror.min.js: $(VENDOR_DIR)/codemirror/dist
	[ -f $(VENDOR_DIR)/codemirror/dist/codemirror.min.js ] && : || \
	curl -sSfLk --get https://cdnjs.cloudflare.com/ajax/libs/codemirror/$(CODEMIRROR_VERSION)/codemirror.min.js \
		-z $(VENDOR_DIR)/codemirror/dist/codemirror.min.js \
		-o $(VENDOR_DIR)/codemirror/dist/codemirror.min.js

$(VENDOR_DIR)/jsplumb: vendor_dir
	[ -d $(VENDOR_DIR)/jsplumb ] && : || \
	git clone --depth 1 --single-branch -b $(JSPLUMB_VERSION) \
		https://github.com/sporritt/jsPlumb.git $(VENDOR_DIR)/jsplumb

$(VENDOR_DIR)/marked: vendor_dir
	[ -d $(VENDOR_DIR)/marked ] && : || \
	git clone --depth 1 --single-branch -b $(MARKED_VERSION) \
		https://github.com/chjj/marked.git $(VENDOR_DIR)/marked

$(VENDOR_DIR)/jquery: vendor_dir
	mkdir -p $(VENDOR_DIR)/jquery

$(VENDOR_DIR)/jquery/jquery-$(JQUERY_VERSION)-min.js: $(VENDOR_DIR)/jquery
	[ -d $(VENDOR_DIR)/jquery/jquery-$(JQUERY_VERSION)-min.js ] && : || \
	curl -sSfLk --get https://cdnjs.cloudflare.com/ajax/libs/jquery/$(JQUERY_VERSION)/jquery.min.js \
		-z $(VENDOR_DIR)/jquery/jquery-$(JQUERY_VERSION)-min.js \
		-o $(VENDOR_DIR)/jquery/jquery-$(JQUERY_VERSION)-min.js

$(VENDOR_DIR)/dojotoolkit: vendor_dir
	[ -d $(VENDOR_DIR)/dojotoolkit ] && : || (\
	rm -rf $(VENDOR_DIR)/dojo-release-$(DOJO_VERSION).tar.gz && \
	curl -sSfLk --get https://download.dojotoolkit.org/release-$(DOJO_VERSION)/dojo-release-$(DOJO_VERSION).tar.gz \
		-z $(VENDOR_DIR)/dojo-release-$(DOJO_VERSION).tar.gz \
		-o $(VENDOR_DIR)/dojo-release-$(DOJO_VERSION).tar.gz && \
	mkdir -p $(VENDOR_DIR)/dojotoolkit && \
	tar -xzf $(VENDOR_DIR)/dojo-release-$(DOJO_VERSION).tar.gz \
		-C $(VENDOR_DIR)/dojotoolkit && \
	rm -f $(VENDOR_DIR)/dojo-release-$(DOJO_VERSION).tar.gz)

$(VENDOR_DIR)/highlightjs: vendor_dir
	mkdir -p $(VENDOR_DIR)/highlightjs

$(VENDOR_DIR)/highlightjs/highlight.min.js: $(VENDOR_DIR)/highlightjs
	[ -f $(VENDOR_DIR)/highlightjs/highlight.min.js ] && : || \
	curl -sSfLk --get http://cdnjs.cloudflare.com/ajax/libs/highlight.js/$(HIGHLIGHT_VERSION)/highlight.min.js \
		-z $(VENDOR_DIR)/highlightjs/highlight.min.js \
		-o $(VENDOR_DIR)/highlightjs/highlight.min.js

$(VENDOR_DIR)/highlightjs/css: $(VENDOR_DIR)/highlightjs
	mkdir -p $(VENDOR_DIR)/highlightjs/css

$(VENDOR_DIR)/highlightjs/css/xcode.min.css: $(VENDOR_DIR)/highlightjs/css
	[ -f $(VENDOR_DIR)/highlightjs/css/xcode.min.css ] && : || \
	curl -sSfLk --get http://cdnjs.cloudflare.com/ajax/libs/highlight.js/$(HIGHLIGHT_VERSION)/styles/xcode.min.css \
		-z $(VENDOR_DIR)/highlightjs/css/xcode.min.css \
		-o $(VENDOR_DIR)/highlightjs/css/xcode.min.css

build: build_thrift_js
build: build_codemirror
build: build_highlightjs
build: build_marked
build: build_jsplumb
build: build_jquery
build: build_dojo

build_dir:
	mkdir -p $(BUILD_DIR)

build_thrift_js: build_dir $(VENDOR_DIR)/thrift
	[ -d $(BUILD_DIR)/thrift ] && : || (\
	mkdir -p $(BUILD_DIR)/thrift && \
	cp $(VENDOR_DIR)/thrift/lib/js/src/thrift.js $(BUILD_DIR)/thrift)

build_codemirror: build_dir $(VENDOR_DIR)/codemirror/dist/codemirror.min.js
	[ -d $(BUILD_DIR)/codemirror ] && : || (\
	cp -r $(VENDOR_DIR)/codemirror $(BUILD_DIR))

build_highlightjs: build_dir $(VENDOR_DIR)/highlightjs/highlight.min.js $(VENDOR_DIR)/highlightjs/css/xcode.min.css
	[ -d $(BUILD_DIR)/highlightjs ] && : || (\
	cp -r $(VENDOR_DIR)/highlightjs $(BUILD_DIR))

build_marked: build_dir $(VENDOR_DIR)/marked
	[ -d $(BUILD_DIR)/marked ] && : || (\
	mkdir -p $(BUILD_DIR)/marked && \
	cp $(VENDOR_DIR)/marked/marked.min.js $(BUILD_DIR)/marked)

build_jsplumb: build_dir $(VENDOR_DIR)/jsplumb
	[ -d $(BUILD_DIR)/jsplumb ] && : || (\
	mkdir -p $(BUILD_DIR)/jsplumb && \
	cp $(VENDOR_DIR)/jsplumb/dist/js/jsPlumb-$(JSPLUMB_VERSION)-min.js $(BUILD_DIR)/jsplumb)

build_jquery: $(VENDOR_DIR)/jquery/jquery-$(JQUERY_VERSION)-min.js build_jsplumb
	[ -d $(BUILD_DIR)/jsplumb/external ] && : || (\
	mkdir -p $(BUILD_DIR)/jsplumb/external && \
	cp $(VENDOR_DIR)/jquery/jquery-$(JQUERY_VERSION)-min.js $(BUILD_DIR)/jsplumb/external)

build_dojo: build_dir $(VENDOR_DIR)/dojotoolkit
	[ -d $(BUILD_DIR)/dojo ] && : || (\
	mkdir -p $(BUILD_DIR)/dojo && \
	cp -r $(VENDOR_DIR)/dojotoolkit/dojo-release-$(DOJO_VERSION)/dijit $(BUILD_DIR)/dojo && \
	cp -r $(VENDOR_DIR)/dojotoolkit/dojo-release-$(DOJO_VERSION)/dojo $(BUILD_DIR)/dojo && \
	cp -r $(VENDOR_DIR)/dojotoolkit/dojo-release-$(DOJO_VERSION)/dojox $(BUILD_DIR)/dojo)

clean: clean_build clean_vendor

clean_build:
	rm -rf $(BUILD_DIR)

clean_vendor:
	rm -rf codemirror
	rm -rf dojotoolkit
	rm -rf highlightjs
	rm -rf jsplumb
	rm -rf jquery
	rm -rf marked
	rm -rf thrift
