import json

from flask import render_template, Blueprint, request, url_for, jsonify

from fuzzer_core.engine.request_builder import RequestBuilder
from fuzzer_core.engine.requester.requester import Requester

main = Blueprint('main', __name__, template_folder='templates')

temp_forwards = {}


@main.route('/')
def index():
    return render_template('contents/index.html')


@main.route('/requester')
def requester():
    from .socket_routes import temps
    # ensure that requester is instantiated again when loading page
    temps['requester'] = None
    return render_template('contents/requester.html')


@main.route('/fuzzer', methods=['POST'])
def fuzzer_forwarding():
    request_data = json.loads(request.json.get('data', {}))
    print(request_data)

    # Check for required fields
    if not (request_data.get('method', None) and request_data.get('url', None)):
        return jsonify({"error": "Missing required data in the request"}), 400
    # try:
    from webapp import fuzzer_conf
    req, auth = RequestBuilder(
        config=fuzzer_conf).build_request(req_dict=request_data)
    if auth is not None:
        # auth_flow generates requests with authentication
        auth_generator = auth.auth_flow(request=req)
        temp_forwards['request_to_fuzzer'] = Requester.reconstruct_request(
            next(auth_generator))
    else:
        temp_forwards['request_to_fuzzer'] = Requester.reconstruct_request(
            req)
    # except Exception:
    #    return jsonify({"error": "Something went wrong when creating the request string"}), 400

    return jsonify({'redirect_url': url_for('main.fuzzer')}), 200


@main.route('/fuzzer')
def fuzzer():
    data = temp_forwards.get('request_to_fuzzer', '')
    temp_forwards['request_to_fuzzer'] = ''
    return render_template('contents/fuzzer.html', request_content=data)


@main.route('/config')
def configuration():
    return render_template('contents/configuration.html')


@main.route('/payload-generator')
def payload_generator():
    return render_template('contents/payload-generator.html')


@main.route('/response-analyser', methods=['POST'])
def response_analyser_forwarding():
    response_content = request.json.get('response_content', '')
    temp_forwards['response_to_analyser'] = response_content
    return jsonify({'redirect_url': url_for('main.response_analyser')})


@main.route('/response-analyser')
def response_analyser():
    data = temp_forwards.get('response_to_analyser', '')
    temp_forwards['response_to_analyser'] = ''
    return render_template('contents/response-analyser.html', response_content=data)


@main.route('/endpoint-discovery')
def api_discovery():
    return render_template('contents/endpoint-discovery.html')


@main.route('/merge-wordlists')
def merge_wordlists():
    return render_template('contents/merge-wordlists.html')


@main.route('/encode-decode')
def encode_decode():
    return render_template('contents/encode-decode.html')


# Define the context processor


def is_active(item, classname='active'):
    url = url = item.get('url', None)
    if url and item['url'] == request.endpoint:
        return classname

    if 'submenu' in item:
        for subitem in item['submenu']:
            sub_active = is_active(subitem, classname)
            if sub_active:
                return sub_active

    return ''


@main.context_processor
def inject_current_route():
    return {'current_route': request.endpoint}


@main.context_processor
def inject_sidebar_helpers():
    return {
        'is_active': is_active,
    }
