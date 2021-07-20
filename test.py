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
    
    if image_list[0] != "kakaobank.harbor.dev":
        image_list[0] = "kakaobank.harbor.dev"

    for i in range(image_cnt):
        image += image_list[i] + "/"
    
    modified_info_object["spec"]["containers"]["image"] = image[:-1]


context = ssl.SSLContext(ssl.PROTOCOL_TLS)
context.load_verify_locations('./ca.crt')
context.load_cert_chain('./server.crt', './server.key')

app.run(host='0.0.0.0', debug=True, ssl_context=context)
