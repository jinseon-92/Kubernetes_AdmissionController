# AdmissionController

## MutatingAdmission & ValidatingAdmission

- MutatingAdmission은 쿠버네티스 클러스터에 요청한 API에 대한 데이터를 임의로 설정한 값으로 변경하는 작업입니다. 또한, 원하는 데이터의 값의 요청을 반려하도록 설정할 수 있습니다. 
- ValidatingAdmission은 쿠버네티스 클러스터에 요청한 API에 대해 반려하고 싶은경우 에러 메시지와 함께 반려하도록 설정할 수 있습니다.

<img width="900" alt="admission-controller-phases" src="https://user-images.githubusercontent.com/58098112/126321675-3fd5bf6b-1dd8-482a-85e9-4f33492a50d9.png">

_출처: https://kubernetes.io/blog/2019/03/21/a-guide-to-kubernetes-admission-controllers_


### 실습

#### Server & Client간에 SSL 통신 설정

- Admission Controller와 Webhook 서버 간 SSL 통신 구현
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
