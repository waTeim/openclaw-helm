-include make.env

IMAGE_REF = $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: configure build push clean

configure:
	python bin/configure-make.py

build:
	docker build --build-arg BASE_IMAGE=$(BASE_IMAGE)  -t $(IMAGE_REF) .

push: build
	docker push $(IMAGE_REF)

clean:
	-docker rmi $(IMAGE_REF)
