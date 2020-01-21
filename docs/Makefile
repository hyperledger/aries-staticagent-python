mkfile_path := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
EXAMPLES = $(abspath $(mkfile_path)../examples)
INCLUDES = $(mkfile_path)_includes
MODULES = $(abspath $(mkfile_path)../aries_staticagent)
PDOC3 = $(shell which pdoc3)
OUTPUT_DIR = $(mkfile_path)

all: html

html:
	@echo 'Generating HTML for $(notdir $(MODULES))'
	$(PDOC3) $(MODULES) --html -o $(OUTPUT_DIR) --force

.PHONY: all
