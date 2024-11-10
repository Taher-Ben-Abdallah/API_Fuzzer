import asyncio
import json
import time

import httpx
from flask_socketio import emit

from fuzzer_core.modules.endpoint_discovery_module import EndpointDiscoveryModule
from fuzzer_core.modules.fuzz_base_module import FuzzBaseModule
from session import Session
from utils.loaders import load_string_to_dict
from webapp import socketio

from utils.encoding_decoding import encode_content, decode_content
from fuzzer_core.engine.response_analyser import ResponseAnalyser
from utils.wordlist_wrapper import Wordlist, process_wordlists_dict
from webapp import fuzzer_conf, session

temps = {}

evt_loop = asyncio.new_event_loop()
asyncio.set_event_loop(evt_loop)

'''#########    MERGE WORDLISTS   #########'''


@socketio.on('start_merge', namespace='/merge-wordlists')
def start_merge(data):
    wordlists = data.get('wordlists', None)
    merge_type = data.get('merge_type', None)
    separator = data.get('separator', None)

    if not all((wordlists, merge_type)):
        emit('merge_result', {'error': 'Options Missing'},
             namespace='/merge-wordlists')
        return

    resul_wordlist = Wordlist.merge_into_wordlist(
        wordlists, merge_type, separator)

    merge_result_data = {"result": resul_wordlist}
    emit('merge_result', merge_result_data, namespace='/merge-wordlists')


@socketio.on('save_merged_wordlist', namespace='/merge-wordlists')
def save_merged_wordlist(data):
    wordlist = data.get('wordlist')

    print('Save wordlist triggered with data:', wordlist)

    save_status = {"status": "Wordlist saved successfully"}
    emit('wordlist_save_status', save_status, namespace='/merge-wordlists')


'''#########    ENCODE DECODE   #########'''


@socketio.on('start_encdec', namespace='/encode-decode')
def encode_decode(data):
    operation = data.get('operation', None)
    method = data.get('method', None)
    content = data.get('content', None)

    # Check for missing fields
    if not all((operation, method, content)):
        emit('encdec_result', {
            'result': 'Missing options!'}, namespace='/encode-decode')
        return

    try:
        if operation == 'encode':
            encdec_result = encode_content(
                content=content, encoding_method=method)
        elif operation == 'decode':
            encdec_result = decode_content(
                content=content, decoding_method=method)
        else:
            encdec_result = 'Invalid operation!'
    except Exception as e:
        encdec_result = f'Error: {str(e)}'

    # Emit the result
    emit('encdec_result', {'result': encdec_result},
         namespace='/encode-decode')


'''#########    RESPONSE ANALYSER   #########'''


@socketio.on('start_analysis', namespace='/response-analyser')
def encode_decode(data):
    content = data.get('response_content', None)
    analysis_result = {}
    if content:
        analysis_result = ResponseAnalyser.extract_response_information(
            response=content)
    emit('analysis_result', {'result': analysis_result},
         namespace='/response-analyser')


'''#########    Payload Generator   #########'''


@socketio.on('start_generation', namespace='/payload-generator')
def start_generation(data):
    print('Start generation process triggered with data:', data)
    type = data.get('type', None)
    gen_invalid = data.get('generate_invalid', True)
    num_payloads = data.get('num_payloads', None)
    gen_details = data.get('gen_details', None)

    merge_result_data = None
    # Call payload generation here

    emit('generation_result', {'result': merge_result_data},
         namespace='/payload-generator')


@socketio.on('save_generated_payloads', namespace='/payload-generator')
def save_generated_payloads(data):
    wordlist = data.get('wordlist')

    print('Save wordlist triggered with data:', wordlist)

    save_status = {"status": "Wordlist saved successfully"}
    emit('gen_payloads_save_status', save_status, namespace='/payload-generator')


'''#########    CONFIGURATION   #########'''


@socketio.on('apply_conf', namespace='/configuration')
def apply_conf(data):
    config = data.get('config', None)
    conf_apply_status = False
    if config:
        try:
            fuzzer_conf.load_config(conf_content=config)
            conf_apply_status = True
        except ValueError:
            conf_apply_status = False

    emit('apply_conf_status', {'status': conf_apply_status},
         namespace='/configuration')


'''#########    SESSION   #########'''


@socketio.on('get_session_status', namespace='/session')
def get_session_status(data):
    """
    Sends the current session status to the client.
    """
    if session is None:
        # No session created or loaded
        emit('session_status', {'status': 'no_session'})
    elif session.active:
        # Session exists and is active
        emit('session_status', {'status': 'active_session', 'session_name': session['session_name'],
                                'session_operations': session['operations']})
    else:
        # Session exists but is inactive
        emit('session_status', {'status': 'inactive_session', 'session_name': session['session_name'],
                                'session_operations': session['operations']}, namespace='/session')


@socketio.on('start_session', namespace='/session')
def start_session(data):
    """
    Starts a session lifecycle, creating a new session if one does not exist.

    Args:
        data (dict): Optionally includes 'config' to create a session if session is None.
    """

    global session
    session_name = data.get('session_name', None)
    if session is None:
        session = Session(session_name=session_name, conf=fuzzer_conf)
    else:
        # Session exists, start a new session lifecycle
        session.start_session()

    emit('session_started', {'message': 'Session started', 'session_operations': session['operations']}, namespace='/session')


@socketio.on('load_session', namespace='/session')
def load_session(data):
    """
    Loads an existing session from the provided dictionary without starting a new lifecycle.

    Args:
        data (dict): Contains 'loaded_session' key with the session data to load.
    """
    global session
    loaded_session_str = data.get('loaded_session', None)
    if loaded_session_str:
        try:
            loaded_session = load_string_to_dict(loaded_session_str)
        except ValueError as e:
            emit('session_error', {'error': str(e)}, namespace='/session')
            return

        # Load the session without starting a new lifecycle entry
        session = Session(loaded_session=loaded_session, conf=fuzzer_conf)
        emit('session_loaded', {'message': 'Session loaded', 'session_name': session['session_name'],
                                'session_operations': session['operations']}, namespace='/session')
    else:
        emit('session_error', {'error': 'No loaded_session data provided'}, namespace='/session')


@socketio.on('end_session', namespace='/session')
def end_session(data):
    """
    Ends the current session by marking it inactive.
    """
    global session
    if session and session.active:
        session.end_session()
        emit('session_ended', {'message': 'Session ended'}, namespace='/session')
    else:
        emit('session_error', {'error': 'No active session to end'}, namespace='/session')


@socketio.on('remove_session', namespace='/session')
def remove_session(data):
    """
    Ends the current session by marking it inactive.
    """
    global session
    if session:
        if session.active:
            session.end_session()
        session = None
        emit('session_removed', {'message': 'session removed'}, namespace='/session')


@socketio.on('save_session', namespace='/session')
def save_session(data):
    """
    Saves the session and sends back the session data as a dictionary.
    """
    global session
    if session:
        session.save()
        emit('session_save', {'session_data': dict(session)}, namespace='/session')
    else:
        emit('session_error', {'error': 'No session to save'}, namespace='/session')


'''#########    Requester   #########'''


@socketio.on('send_request', namespace='/requester')
def send_request(data):
    print(data)
    request_data = json.loads(data.get('request_data', None))
    proxy = data.get('proxy', None)
    if not (request_data['method'] and request_data['url']):
        print('request data missing required fields')
        return  # end function here

    # Avoid circular import in file
    from fuzzer_core.engine.requester.requester import Requester

    requester = temps.get('requester', None)
    if requester is None:
        requester = Requester(config=fuzzer_conf, follow_redirects=True, proxy=proxy)
        temps['requester'] = requester
    try:
        response = asyncio.run(requester.prepare_and_send(request_data))

        print('AFTER asyncio')
        print(type(response))
        while not isinstance(response, httpx.Response):
            print(type(response))

        emit('send_request_result', {
            'response': Requester.reconstruct_response(response),
            'elapsed_time': response.elapsed.total_seconds()
        }, namespace='/requester')

    except Exception as e:
        print(f"Error while awaiting response: {e}")
        emit('send_request_result', {
            'error': 'Error in sending request'}, namespace='/requester')


'''#########    Endpoint Discovery   #########'''


@socketio.on('start_discovery', namespace='/endpoint-discovery')
def start_discovery(data):
    print(data)
    path = data.get('path', None)
    depth = data.get('depth', None)

    num_workers = data.get('num_workers', 1)
    response_analysis = {'matching_requirements': data.get('match_hide', None)}
    rate_limiting = data.get('rate_conc_limit', None)

    wordlist = data.get('wordlist').splitlines() if data.get('wordlist', None) is not None else None
    proxy = data.get('proxy', None)

    discovery_module = EndpointDiscoveryModule(wordlists=wordlist, response_analysis=response_analysis,
                                               rate_limiting=rate_limiting, num_workers=num_workers, depth=depth,
                                               config=fuzzer_conf)

    results = []
    emit('discovery_results', {'results': results}, namespace='/endpoint-discovery')


'''#########    Fuzzer   #########'''


def backgound_fuzz(fuzz_base_module, request_details, iterator):
    asyncio.run(fuzz_base_module.run_fuzz(req_details=request_details, iterator=iterator))


@socketio.on('start_fuzz', namespace='/fuzzer')
def start_fuzz(data):
    print(data)
    columns = data.get('analysis', None)

    num_workers = data.get('num_workers', 1)
    response_analysis = {'analysis_parameters': data.get('analysis', None),
                         'matching_requirements': data.get('match_hide', None)}
    print(response_analysis)

    rate_limiting = data.get('rate_conc_limit', None)
    wordlists = process_wordlists_dict(data.get('wordlists', None))

    request_details = data.get('request_details', None)
    iterator = data.get('iterator', None)

    proxy = data.get('proxy', None)

    http_version = {'v1': True, 'v2': False}
    version = data.get('http_version', None)
    if version is not None and version in ('HTTP/1.1', 'HTTP/2'):
        http_version = {'v1': version == 'HTTP/1.1', 'v2': version == 'HTTP/2'}

    fuzz_base_module = FuzzBaseModule(num_workers=num_workers, response_analysis=response_analysis, wordlists=wordlists,
                                      rate_limiting=rate_limiting, config=fuzzer_conf, proxy=proxy, http_version=http_version)

    asyncio.run(fuzz_base_module.run_fuzz(req_details=request_details, iterator=iterator))
    # Thread(target=backgound_fuzz, args=(request_details, iterator,response_analysis,rate_limiting,fuzzer_conf,proxy,http_version,num_workers,wordlists))
    # socketio.start_background_task(backgound_fuzz, fuzz_base_module, request_details, iterator)

    # loop = asyncio.get_event_loop()
    # asyncio.run_coroutine_threadsafe(fuzz_base_module.run_fuzz(req_details=request_details, iterator=iterator),loop)
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # loop.run_until_complete(fuzz_base_module.run_fuzz(req_details=request_details, iterator=iterator))

    temps['fuzz_base_module'] = fuzz_base_module

    responses = []
    start_time = time.time()

    # Use the generator to collect items from the queue
    for _, analysis in fuzz_base_module.base_fuzz_results():
        print('BEFORE IF ANALYSIS')
        if analysis:
            responses.append(analysis)
        # Check if 1 seconds have passed to emit the current batch
        if time.time() - start_time >= 1:
            if responses:
                print(responses)
                emit('fuzz_responses', {'responses': responses})
                responses = []  # Reset the list after emission
            start_time = time.time()  # Reset the timer
    # Final emit in case there are any leftover responses after finishing the loop
    if responses:
        emit('fuzz_responses', {'responses': responses})


@socketio.on('pause_resume', namespace='/fuzzer')
def pause_resume(data):
    # Check the command from client and toggle the `is_paused` state
    if data.get('change_status') in ('pause', 'resume'):
        fuzz_base_module = temps.get('fuzz_base_module', None)
        '''
        Just for test 
        if fuzz_base_module.is_paused is None:
            fuzz_base_module.run_fuzz({}, '')'''
        if fuzz_base_module is not None and fuzz_base_module.is_paused is not None:
            fuzz_base_module.toggle_is_paused()
            emit('pause_resume_status', {'is_paused': fuzz_base_module.is_paused})
