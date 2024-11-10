from httpx import Client

from fuzzer_core.engine.requester.auth import prepare_auth


# from engine.requester.requester import prepare_files

def merge_dicts(common, default):
    """
    Merges the common (for all reqs) and default values (from config)
    :param common:
    :param default:
    :return:
    """

    if not common and not default:
        return None

    merged_dicts = common.copy()

    for subdict_key, subdict_val in default.items():
        print("KEY: ", subdict_key)
        print("VAL: ", subdict_val)
        if subdict_key in merged_dicts:

            # Managing auth separately: needs to be a list of dicts ( not a merged dict)
            # this makes sure that the auth items are merged correctly
            if subdict_key == 'auth':
                merged_auth = merged_dicts[subdict_key]
                default_auth = subdict_val
                if isinstance(merged_auth, list) and isinstance(default_auth, list):
                    merged_dicts[subdict_key].extend(default_auth)
                elif isinstance(merged_auth, dict) and isinstance(default_auth, dict):
                    merged_dicts[subdict_key] = [merged_auth, default_auth]
                else:
                    try:
                        # appending dict to list
                        merged_dicts[subdict_key].append(default_auth)
                    except AttributeError:
                        # merging dict and list into list
                        merged_dicts[subdict_key] = [merged_auth] + default_auth

                continue

            if isinstance(subdict_val, list):
                if isinstance(merged_dicts[subdict_key], list):
                    merged_dicts[subdict_key].extend(subdict_val)
                else:
                    merged_dicts[subdict_key].append(subdict_val)
                continue
            if not isinstance(subdict_val, dict):
                # If same item present in default and the other dict, ignore default value
                continue

            for key, value in subdict_val.items():
                if key not in merged_dicts[subdict_key]:
                    merged_dicts[subdict_key][key] = value
        else:
            merged_dicts[subdict_key] = subdict_val.copy()

    return merged_dicts


class RequestBuildError(BaseException):
    pass


class RequestBuilder:

    def __init__(self, common_fields=None, config=None):
        super().__init__()

        common_fields = common_fields or {}
        config = config or {}

        """
        "common_fields": {
                            - headers
                            - params
                            - cookies
                            - base_url
                            - auth just the credentials because build_request doesn't merge auth (client.send() does)
                        }
        """
        self.auth = None
        self.merged_fields = merge_dicts(common_fields, config.get("request", {}))
        if self.merged_fields is None:
            self.client = Client()
        else:
            self.client = Client(base_url=self.merged_fields.get('base_url', ''),
                                 headers=self.merged_fields.get('headers', None),
                                 params=self.merged_fields.get('params', None),
                                 cookies=self.merged_fields.get('cookies', None))

            if "auth" in self.merged_fields.keys():
                self.auth = prepare_auth(self.merged_fields["auth"])

    def build_request(self, req_dict: dict) -> tuple:
        """
        Builds request from dictionary passed as argument
        Dict can have values for each section of the request,
        OR just url, method, and contents(case of raw request provided)

        :param req_dict:
        :return: tuple (req,auth)
        """

        """
        *The `params`, `headers` and `cookies` arguments are merged with any values set on the client.
        *The `url` argument is merged with any `base_url` set on the client.
        """

        c = Client() if self.client is None else self.client

        try:

            files = None
            req_files = req_dict.get('files', None)
            # Preparing files
            """if req_files is not None:
                # if the files is a dict or tuple of a single file, puts it in a list
                files = prepare_files(req_files if isinstance(req_files, list) else [req_files])"""

            req = c.build_request(method=req_dict.get("method"), url=req_dict.get("url"),
                                  params=req_dict.get("params", None), headers=req_dict.get("headers", None),
                                  cookies=req_dict.get("cookies", None), content=req_dict.get("content", None),
                                  data=req_dict.get("data", None), json=req_dict.get("json", None), files=files)

            # Preparing request authentication
            # auth is of (httpx.Auth,httpx_auth.SupportMultiAuth) object type

            if req_dict.get("auth", None) is not None:
                auth = prepare_auth(req_dict.get("auth")) + self.auth if self.auth is not None else prepare_auth(
                    req_dict.get("auth"))
            else:
                auth = self.auth

        except KeyError:
            print("request dictionary missing required information")
            raise RequestBuildError

        return req, auth

    def build_requests(self, reqs: list[dict]):

        """
         "reqs": [{},{},...]
        """
        for request in reqs:
            yield self.build_request(request)
