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
build:	build_3_10 build_3_11 build_3_12 ## Build all Python containers

.PHONY: build_3_10
build_3_10: ## Build Python 3.10 container
	docker build --platform=linux/amd64 --build-arg GIT_REF=${GIT_REF} -t ${NAME}_py_3_10:${GIT_REF} -t ${NAME}_py_3_10:latest -f py3.10/Dockerfile .

.PHONY: build_3_11
build_3_11: ## Build Python 3.11 container
	docker build --platform=linux/amd64 --build-arg GIT_REF=${GIT_REF} -t ${NAME}_py_3_11:${GIT_REF} -t ${NAME}_py_3_11:latest -f py3.11/Dockerfile .

.PHONY: build_3_12
build_3_12: ## Build Python 3.12 container
	docker build --platform=linux/amd64 --build-arg GIT_REF=${GIT_REF} -t ${NAME}_py_3_12:${GIT_REF} -t ${NAME}_py_3_12:latest -f py3.12/Dockerfile .

.PHONY: build_shell
build_shell: ## Build Python 3.11 container
	docker build --platform=linux/amd64 --build-arg GIT_REF=${GIT_REF} -t ${NAME}_shell:${GIT_REF} -t ${NAME}_shell:latest -f shell/Dockerfile .

.PHONY: test
test: test_predict test_3_10 test_3_11 test_3_12 ## Test all container versions

.PHONY: test_predict
test_predict: build_shell ## Test predict script
	docker run -i --rm -v ./tests/:/tests/ -v /tmp:/tmp ${NAME}_shell:latest python -m unittest tests.test_predict

.PHONY: test_3_10
test_3_10: build_3_10 ## Test Python 3.10 pickle
	docker run -i --rm -v ./tests/:/tests/ -v /tmp:/tmp ${NAME}_py_3_10:latest --model /tests/models/model_3_10_legacy.pkl
	docker run -i --rm -v ./tests/:/tests/ -v /tmp:/tmp ${NAME}_py_3_10:latest --model /tests/models/model_3_10.pkl

.PHONY: test_3_11
test_3_11: build_3_11 ## Test Python 3.11 pickle
	docker run -i --rm -v ./tests/:/tests/ -v /tmp:/tmp ${NAME}_py_3_11:latest --model /tests/models/model_3_11_legacy.pkl
	docker run -i --rm -v ./tests/:/tests/ -v /tmp:/tmp ${NAME}_py_3_11:latest --model /tests/models/model_3_11.pkl

.PHONY: test_3_12
test_3_12: build_3_12 ## Test Python 3.12 pickle
	docker run -i --rm -v ./tests/:/tests/ -v /tmp:/tmp ${NAME}_py_3_12:latest --model /tests/models/model_3_12_legacy.pkl
	docker run -i --rm -v ./tests/:/tests/ -v /tmp:/tmp ${NAME}_py_3_12:latest --model /tests/models/model_3_12.pkl

.PHONY: push_latest
push_latest: push_latest_3_10 push_latest_3_11 push_latest_3_12 ## Push latest docker containers

.PHONY: push_latest_3_10
push_latest_3_10: build_3_10 ## Release Python 3.10 container tagged latest
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_10:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_10:${GIT_REF}
	docker tag ${NAME}_py_3_10:latest ${ECR_REPO}/${NAME}_py_3_10:latest
	docker push ${ECR_REPO}/${NAME}_py_3_10:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_10:latest

.PHONY: push_latest_3_11
push_latest_3_11: build_3_11 ## Release Python 3.11 container tagged latest
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_11:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_11:${GIT_REF}
	docker tag ${NAME}_py_3_11:latest ${ECR_REPO}/${NAME}_py_3_11:latest
	docker push ${ECR_REPO}/${NAME}_py_3_11:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_11:latest

.PHONY: push_latest_3_12
push_latest_3_12: build_3_12 ## Release Python 3.12 container tagged latest
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_12:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_12:${GIT_REF}
	docker tag ${NAME}_py_3_12:latest ${ECR_REPO}/${NAME}_py_3_12:latest
	docker push ${ECR_REPO}/${NAME}_py_3_12:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_12:latest

.PHONY: push_latest_shell
push_latest_shell: build_shell ## Release Python 3.11 container tagged latest
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_shell:${GIT_REF} ${ECR_REPO}/${NAME}_shell:${GIT_REF}
	docker tag ${NAME}_shell:latest ${ECR_REPO}/${NAME}_shell:latest
	docker push ${ECR_REPO}/${NAME}_shell:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_shell:latest

.PHONY: push_stable
push_stable: push_stable_3_9 push_stable_3_10 push_stable_3_11 ## Push all container tagged stable

.PHONY: push_stable_3_10
push_stable_3_10: build_3_10 ## Release Python 3.10 container tagged stable
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_10:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_10:${GIT_REF}
	docker tag ${NAME}_py_3_10:latest ${ECR_REPO}/${NAME}_py_3_10:stable
	docker push ${ECR_REPO}/${NAME}_py_3_10:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_10:stable

.PHONY: push_stable_3_11
push_stable_3_11: build_3_11## Release Python 3.11 container tagged stable
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_11:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_11:${GIT_REF}
	docker tag ${NAME}_py_3_11:latest ${ECR_REPO}/${NAME}_py_3_11:stable
	docker push ${ECR_REPO}/${NAME}_py_3_11:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_11:stable

.PHONY: push_stable_3_12
push_stable_3_12: build_3_12 ## Release Python 3.12 container tagged stable
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_12:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_12:${GIT_REF}
	docker tag ${NAME}_py_3_12:latest ${ECR_REPO}/${NAME}_py_3_12:stable
	docker push ${ECR_REPO}/${NAME}_py_3_12:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_12:stable
