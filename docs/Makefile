mkfile_path := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
EXAMPLES = $(abspath $(mkfile_path)../examples)
INCLUDES = $(mkfile_path)_includes
MODULES = $(abspath $(mkfile_path)../aries_staticagent)
PDOC3 = $(shell which pdoc3)
OUTPUT_DIR = $(mkfile_path)

all: html examples

html:
	@echo 'Generating HTML for $(notdir $(MODULES))'
	$(PDOC3) $(MODULES) --html -o $(OUTPUT_DIR) --force


examples:
	@echo $(INCLUDES) $(EXAMPLES)
	mkdir -p $(INCLUDES)/examples
	cp $(EXAMPLES)/* $(INCLUDES)/examples/.


.PHONY: all examples
