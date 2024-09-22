NAME		:= numerai_predict
ECR_REPO	:= ${ACCOUNT_ID}.dkr.ecr.us-west-2.amazonaws.com
GIT_REF     	:= $$(git rev-parse --short HEAD)
.DEFAULT_GOAL   := help

.PHONY: help
help:
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: lint
lint: ## Run linter
	ruff check . --fix

.PHONY: build
build:	build_3_9 build_3_10 build_3_11 ## Build all Python containers

.PHONY: build_3_9
build_3_9: ## Build Python 3.9 container
	docker build --build-arg GIT_REF=${GIT_REF} -t ${NAME}_py_3_9:${GIT_REF} -t ${NAME}_py_3_9:latest -f py3.9/Dockerfile .

.PHONY: build_3_10
build_3_10: ## Build Python 3.10 container
	docker build --build-arg GIT_REF=${GIT_REF} -t ${NAME}_py_3_10:${GIT_REF} -t ${NAME}_py_3_10:latest -f py3.10/Dockerfile .

.PHONY: build_3_11
build_3_11: ## Build Python 3.11 container
	docker build --build-arg GIT_REF=${GIT_REF} -t ${NAME}_py_3_11:${GIT_REF} -t ${NAME}_py_3_11:latest -f py3.11/Dockerfile .

.PHONY: test
test: test_3_9 test_3_10 test_3_11 ## Test all container versions

.PHONY: test_3_9
test_3_9: build_3_9 ## Test Python 3.9 pickle
	docker run -i --rm -v ${PWD}:${PWD} -v /tmp:/tmp ${NAME}_py_3_9:latest --model ${PWD}/tests/models/model_3_9_legacy.pkl
	docker run -i --rm -v ${PWD}:${PWD} -v /tmp:/tmp ${NAME}_py_3_9:latest --model ${PWD}/tests/models/model_3_9.pkl

.PHONY: test_3_10
test_3_10: build_3_10 ## Test Python 3.10 pickle
	docker run -i --rm -v ${PWD}:${PWD} -v /tmp:/tmp ${NAME}_py_3_10:latest --model ${PWD}/tests/models/model_3_10_legacy.pkl
	docker run -i --rm -v ${PWD}:${PWD} -v /tmp:/tmp ${NAME}_py_3_10:latest --model ${PWD}/tests/models/model_3_10.pkl

.PHONY: test_3_11
test_3_11: build_3_11 ## Test Python 3.11 pickle
	docker run -i --rm -v ${PWD}:${PWD} -v /tmp:/tmp ${NAME}_py_3_11:latest --model ${PWD}/tests/models/model_3_11_legacy.pkl
	docker run -i --rm -v ${PWD}:${PWD} -v /tmp:/tmp ${NAME}_py_3_11:latest --model ${PWD}/tests/models/model_3_11.pkl

test_validation_%: build_% ## Test validation dataset
	docker run -i --rm -v ${PWD}:${PWD} -v /tmp:/tmp ${NAME}_py_$*:latest \
		--dataset v4.3/validation_int8.parquet --benchmarks v4.3/validation_benchmark_models.parquet \
		--model ${PWD}/tests/models/model_$*_legacy.pkl

.PHONY: test_validation
test_validation: test_validation_3_9 test_validation_3_10 test_validation_3_11

.PHONY: push_latest
push_latest: push_latest_3_9 push_latest_3_10 push_latest_3_11 ## Push latest docker containers

.PHONY: push_latest_3_9
push_latest_3_9: build_3_9 ## Push Python 3.9 contianer tagged latest
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_9:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_9:${GIT_REF}
	docker tag ${NAME}_py_3_9:latest ${ECR_REPO}/${NAME}_py_3_9:latest
	docker push ${ECR_REPO}/${NAME}_py_3_9:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_9:latest

.PHONY: push_latest_3_10
push_latest_3_10: build_3_10 ## Release Python 3.10 contianer tagged latest
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_10:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_10:${GIT_REF}
	docker tag ${NAME}_py_3_10:latest ${ECR_REPO}/${NAME}_py_3_10:latest
	docker push ${ECR_REPO}/${NAME}_py_3_10:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_10:latest

.PHONY: push_latest_3_11
push_latest_3_11: build_3_11## Release Python 3.11 contianer tagged latest
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_11:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_11:${GIT_REF}
	docker tag ${NAME}_py_3_11:latest ${ECR_REPO}/${NAME}_py_3_11:latest
	docker push ${ECR_REPO}/${NAME}_py_3_11:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_11:latest

.PHONY: push_stable
push_stable: push_stable_3_9 push_stable_3_10 push_stable_3_11 ## Push all container tagged stable

.PHONY: push_stable_3_9
push_stable_3_9: build_3_9 ## Release Python 3.9 contianer tagged stable
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_9:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_9:${GIT_REF}
	docker tag ${NAME}_py_3_9:latest ${ECR_REPO}/${NAME}_py_3_9:stable
	docker push ${ECR_REPO}/${NAME}_py_3_9:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_9:stable

.PHONY: push_stable_3_10
push_stable_3_10: build_3_10 ## Release Python 3.10 contianer tagged stable
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_10:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_10:${GIT_REF}
	docker tag ${NAME}_py_3_10:latest ${ECR_REPO}/${NAME}_py_3_10:stable
	docker push ${ECR_REPO}/${NAME}_py_3_10:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_10:stable

.PHONY: push_stable_3_11
push_stable_3_11: build_3_11## Release Python 3.11 contianer tagged stable
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_11:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_11:${GIT_REF}
	docker tag ${NAME}_py_3_11:latest ${ECR_REPO}/${NAME}_py_3_11:stable
	docker push ${ECR_REPO}/${NAME}_py_3_11:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_11:stable
