NAME		:= numerai_predict
ECR_REPO	:= 584380190766.dkr.ecr.us-west-2.amazonaws.com
GIT_REF     	:= $$(git rev-parse --short HEAD)
.DEFAULT_GOAL   := help

.PHONY: help
help:
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: build
build:	build_3_9 build_3_10 build_3_11 ## Build all Python containers

.PHONY: build_3_9
build_3_9: ## Build Python 3.9 container
	docker build -t ${NAME}_py_3_9:${GIT_REF} -t ${NAME}_py_3_9:latest -f py3.9/Dockerfile .

.PHONY: build_3_10
build_3_10: ## Build Python 3.10 container
	docker build -t ${NAME}_py_3_10:${GIT_REF} -t ${NAME}_py_3_10:latest -f py3.10/Dockerfile .

.PHONY: build_3_11
build_3_11: ## Build Python 3.11 container
	docker build -t ${NAME}_py_3_11:${GIT_REF} -t ${NAME}_py_3_11:latest -f py3.11/Dockerfile .

.PHONY: test
test: test_3_9 test_3_10 test_3_11 ## Test all container versions

.PHONY: test_3_9
test_3_9: build_3_9 ## Test Python 3.9 pickle
	docker run -i --rm -v ${PWD}:${PWD} -v /tmp:/tmp ${NAME}_py_3_9:latest --model ${PWD}/tests/models/model_3_9.pkl

.PHONY: test_3_10
test_3_10: build_3_10 ## Test Python 3.10 pickle
	docker run -i --rm -v ${PWD}:${PWD} -v /tmp:/tmp ${NAME}_py_3_10:latest --model ${PWD}/tests/models/model_3_10.pkl

.PHONY: test_3_11
test_3_11: build_3_11 ## Test Python 3.11 pickle
	docker run -i --rm -v ${PWD}:${PWD} -v /tmp:/tmp ${NAME}_py_3_11:latest --model ${PWD}/tests/models/model_3_11.pkl

.PHONY: release
release: release_3_9 release_3_10 release_3_11 ## Push all container tagged releases

.PHONY: release_3_9
release_3_9: ## Release Python 3.9 contianer tagged release
	docker build -t ${NAME}_py_3_9:${GIT_REF} -t ${NAME}_py_3_9:latest -f py3.9/Dockerfile .
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_9:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_9:${GIT_REF}
	docker tag ${NAME}_py_3_9:latest ${ECR_REPO}/${NAME}_py_3_9:latest
	docker push ${ECR_REPO}/${NAME}_py_3_9:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_9:latest

.PHONY: release_3_10
release_3_10: ## Release Python 3.10 contianer tagged release
	docker build -t ${NAME}_py_3_10:${GIT_REF} -t ${NAME}_py_3_10:latest -f py3.10/Dockerfile .
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_10:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_10:${GIT_REF}
	docker tag ${NAME}_py_3_10:latest ${ECR_REPO}/${NAME}_py_3_10:latest
	docker push ${ECR_REPO}/${NAME}_py_3_10:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_10:latest

.PHONY: release_3_11
release_3_11: ## Release Python 3.11 contianer tagged release
	docker build -t ${NAME}_py_3_11:${GIT_REF} -t ${NAME}_py_3_11:latest -f py3.11/Dockerfile .
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_11:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_11:${GIT_REF}
	docker tag ${NAME}_py_3_11:latest ${ECR_REPO}/${NAME}_py_3_11:latest
	docker push ${ECR_REPO}/${NAME}_py_3_11:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_11:latest
