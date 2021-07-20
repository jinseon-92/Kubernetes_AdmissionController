# AdmissionController

## MutatingAdmission & ValidatingAdmission

- MutatingAdmission은 쿠버네티스 클러스터에 요청한 API에 대한 데이터를 임의로 설정한 값으로 변경하는 작업입니다. 또한, 원하는 데이터의 값의 요청을 반려하도록 설정할 수 있습니다. 
- ValidatingAdmission은 쿠버네티스 클러스터에 요청한 API에 대해 반려하고 싶은경우 에러 메시지와 함께 반려하도록 설정할 수 있습니다.

<img width="900" alt="admission-controller-phases" src="https://user-images.githubusercontent.com/58098112/126321675-3fd5bf6b-1dd8-482a-85e9-4f33492a50d9.png">

_출처: https://kubernetes.io/blog/2019/03/21/a-guide-to-kubernetes-admission-controllers_






### 실습

- Image Repogitory를 검증하여 jinseon.harbor.dev 경로와 다른 Repogitory 경로로 요청할 경우 수정하도록 설정
- jinseon.harbor.prd Repogitory Image 사용 시 요청을 반려하도록 설정
---

##### Admission Controller와 Webhook 서버 간 SSL 통신 구현
```
mkdir mutating
cd mutating

openssl genrsa -out ca.key 2048
openssl req -x509 -new -nodes -key ca.key -days 100000 -out ca.crt -subj "/CN=admission_ca"


cat >server.conf <<EOF
[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name
prompt = no
[req_distinguished_name]
CN = mutating.default.svc         # Servcie 리소스 도메인 
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth, serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = mutating.default.svc      # Service 리소스 도메인
EOF

openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -config server.conf

openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 100000 -extensions v3_req -extfile server.conf
```
---


##### Webhook 서버 구현 (Python_Flask)

```
vi test.py

from flask import Flask, request, jsonify
from pprint import pprint
import jsonpatch
import base64
import copy
import ssl


app = Flask(__name__)

@app.route('/', methods=['POST'])
def webhook():
    request_info = request.json
    request_info_object = request_info["request"]["object"]

    modified_info = copy.deepcopy(request_info)
    pprint(modified_info)
    modified_info_object = modified_info["request"]["object"]

    if modified_info_object["metadata"]["annotations"][0]["stage"] is dev:
        check_dev_image(modified_info_object)
        patch = jsonpatch.JsonPatch.from_diff(request_info_object, modified_info_object)

        admissionReview = {
            "response": {
                "allowed": True,
                "uid": request_info["request"]["uid"],
                "patch": base64.b64encode(str(patch).encode()).decode(),
                "patchtype": "JSONPatch"
            }
        }
        return jsonify(admissionReview)

    else if modified_info_object["metadata"]["annotations"][0]["stage"] is prod:
        admissionReview = {
            "response": {
                "allowed": False,
                "uid": request_info["request"]["uid"],
                "patch": base64.b64encode(str(patch).encode()).decode(),
                "patchtype": "JSONPatch"
            }
        }
        return jsonify(admissionReview)

    else
        admissionReview = {
            "response": {
                "allowed": False,
                "uid": request_info["request"]["uid"],
                "patch": base64.b64encode(str(patch).encode()).decode(),
                "patchtype": "JSONPatch"
            }
        }
        return jsonify(admissionReview)


def check_dev_image(modified_info_object):
    image = modified_info_object["spec"]["containers"]["image"]
    image_list = image.split('/')
    image_cnt = len(image_list)

    if image_list[0] != "jinseon.harbor.dev":
        image_list[0] = "jinseon.harbor.dev"

    for i in range(image_cnt):
        image += image_list[i] + "/"

    modified_info_object["spec"]["containers"]["image"] = image[:-1]


context = ssl.SSLContext(ssl.PROTOCOL_TLS)
context.load_verify_locations('./ca.crt')
context.load_cert_chain('./server.crt', './server.key')

app.run(host='0.0.0.0', debug=True, ssl_context=context)
```
---


##### Dockerfile 작성

```
vi Dockerfile

FROM python:3.8

COPY requirements.txt /
RUN pip install -r requirements.txt

ADD test.py .
ADD server.key .
ADD server.crt .
ADD ca.crt .

CMD ["python", "-u", "test.py"]
```
---


##### requirements.txt 작성

```
vi requirements.txt

flask
```
---


##### 도커 Image Build

```
docker build -t [이미지:버전]     # ex) jinseon/mutating:1.0
docker push [이미지:버전]
```
---


##### 쿠버네티스 클러스터에 Webhook 리소스 배포 (service, pod)

```
vi mutating.yaml

kind: Service
apiVersion: v1
metadata:
  name: mutating
  namespace: default
spec:
  selector:
    app: mutating
  ports:
  - name: https
    protocol: TCP
    port: 443
    targetPort: 5000
---
apiVersion: v1
kind: Pod
metadata:
  name: mutating
  labels:
    app: mutating
spec:
  containers:
  - name: mutating
    image: [이미지:버전]


kubectl apply -f mutating.yaml
```
---


##### MutatingWebhookConfiguration 작성

```
cat > mutatingwebhook.yaml <<EOF
# mutatingwebhook.yaml
kind: ValidatingWebhookConfiguration
apiVersion: admissionregistration.k8s.io/v1beta1
metadata:
  name: mutating
webhooks:
  - name: mutating.jinseon.com
    namespaceSelector:
      matchExpressions:
      - key: openpolicyagent.org/mutating
        operator: NotIn
        values:
        - ignore
    rules:
      - operations: ["CREATE"]
        apiGroups: ["*"]
        apiVersions: ["*"]
        resources: ["deployments"]
    clientConfig:
      caBundle: $(cat ca.crt | base64 | tr -d '\n')
      service:
        namespace: default
        name: mutating
EOF

kubectl apply -f mutatingwebhook.yaml
```
---


##### 테스트 Deployment 리소스 배포

```
vi deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  labels:
    app: nginx
  annotations:
    stage: dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: quay.io/jaegertracing/jaeger-collector:1.24
        ports:
        - containerPort: 80


kubectl apply -f deployment.yaml
```
