CONFIG = build-config.json

ifneq ($(wildcard $(CONFIG)),)
BASE_IMAGE := $(shell python3 -c "import json;c=json.load(open('$(CONFIG)'));s=c['source'];print(s['registry']+'/'+s['image']+':'+s['tag'])")
REGISTRY   := $(shell python3 -c "import json;print(json.load(open('$(CONFIG)'))['target']['registry'])")
IMAGE_NAME := $(shell python3 -c "import json;print(json.load(open('$(CONFIG)'))['target']['image'])")
IMAGE_TAG  := $(shell python3 -c "import json;print(json.load(open('$(CONFIG)'))['target']['tag'])")
endif

IMAGE_REF = $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: configure build push clean

configure:
	python3 bin/configure.py

build:
	docker build --platform=linux/amd64 --build-arg BASE_IMAGE=$(BASE_IMAGE) -t $(IMAGE_REF) .

push: build
	docker push $(IMAGE_REF)

clean:
	-docker rmi $(IMAGE_REF)
