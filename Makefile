build:	build_3_9 build_3_10 build_3_11

build_3_9: 
	docker build -t numerai_predict_py3.9 -f py3.9/Dockerfile .

build_3_10: 
	docker build -t numerai_predict_py3.10 -f py3.10/Dockerfile .

build_3_11: 
	docker build -t numerai_predict_py3.11 -f py3.11/Dockerfile .

test: test_3_9 test_3_10 test_3_11

test_3_9: build_3_9
	docker run -i --volume /tmp:/tmp numerai_predict_py3.9 --model https://huggingface.co/pschork/hello-numerai-models/resolve/main/model_3.9.pkl 

test_colab: build_3_9
	docker run -i --volume /tmp:/tmp numerai_predict_py3.9 --model https://huggingface.co/pschork/hello-numerai-models/resolve/main/colab_3.9.16.pkl 

test_3_10: build_3_10
	docker run -i --volume /tmp:/tmp numerai_predict_py3.10 --model https://huggingface.co/pschork/hello-numerai-models/resolve/main/model_3.10.pkl 

test_3_11: build_3_11
	docker run -i --volume /tmp:/tmp numerai_predict_py3.11 --model https://huggingface.co/pschork/hello-numerai-models/resolve/main/model_3.11.pkl 
