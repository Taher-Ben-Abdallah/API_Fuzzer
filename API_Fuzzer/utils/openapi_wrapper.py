"""
Wrapper for Swagger 2.0 and OpenAPI 3.0 formats
"""

from collections import defaultdict
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

import yaml

# TODO:
#  - General security and security schemas to add to endpoints security


""" https://github.com/RUB-NDS/REST-Attacker/tree/main """


class SecuritySchemeNotFound(Exception):
    pass


class OpenAPISpec:
    """
    Wrapper Class for an OpenAPI definition.
    Takes processed spec file content into a dictionary
    """

    def __init__(self, description_id: str, content: dict) -> None:
        """
        Create a new OpenAPI description.

        :param description_id: Identifier for the description.
        :type description_id: str
        :param content: Content of the description file.
        :type content: dict
        """
        self.description_id = description_id
        self.definition = content

        self.version = None
        if "swagger" in self.definition.keys():
            if self.definition["swagger"] == "2.0":
                self.version = self.definition["swagger"]
                self.transform()

        elif "openapi" in self.definition.keys():
            self.version = self.definition["openapi"]

        else:
            raise Exception("Could not find version in OpenAPI description.")

        self.general_security = None

    def transform(self) -> None:
        """
        Transform the format from swagger 2.0 to OpenAPI 3.0.
        """
        # Multiple hosts are supported
        host = self.definition.pop("host")
        base_path = self.definition.pop("basePath")
        schemes = self.definition.pop("schemes")

        servers = []
        for scheme in schemes:
            server_url = f"{scheme}://{host}{base_path}"
            servers.append({"url": server_url})

        self.definition["servers"] = servers

        global_consumes = self.definition.pop("consumes", [])
        global_produces = self.definition.pop("produces", [])
        for path in self.definition["paths"].values():
            for method in path.values():
                local_consumes = method.pop("consumes", [])
                if len(local_consumes) == 0:
                    if len(global_consumes) == 0:
                        local_consumes = []

                    else:
                        local_consumes = global_consumes[0]

                input_parameters = method.pop("parameters", [])
                if len(input_parameters) > 0:
                    response_body = None
                    response_form = None
                    for param in input_parameters:
                        if param["in"] == "body":
                            response_body = {
                                "description": param["description"],
                                "content": {
                                    local_consumes: param["schema"]
                                }
                            }

                        elif param["in"] == "form":
                            response_form = {
                                "description": param["description"],
                                "content": {
                                    local_consumes: param["schema"]
                                }
                            }

                    if response_body:
                        method["responseBody"] = response_body

                    if response_form:
                        method["responseForm"] = response_form

                for response in method["responses"].values():
                    response_schema = response.pop("schema", [])
                    if response_schema:
                        response.update({
                            "content": {
                                global_produces[0]: response_schema
                            }
                        })

    def resolve_ref(self, ref: str) -> None | dict:
        """
        Get the referenced object to a relative reference. The reference can be an
        URI or a JSON pointer (RFC 6901).

        :param ref: Reference URI.
        :type ref: str
        """
        if ref[0] == "#":
            # JSON pointer
            # Remove URI encoding
            new_ref = unquote(ref)

            # Split into parts
            parts = new_ref[2:].split('/')

            # Start at root
            current_item = self.definition
            for part in parts:
                # Replace escaped symbols_ '~', '/'
                part_ref = part.replace('~0', '~')
                part_ref = part_ref.replace("~1", "/")

                if isinstance(current_item, dict):
                    # JSON object
                    current_item = current_item[part_ref]

                elif isinstance(current_item, list):
                    # JSON array
                    current_item = current_item[int(part_ref)]

                else:
                    raise Exception(f"Item at {part} in {new_ref} must be a JSON object or array.")

            return current_item

        # TODO: External references
        return None

    def get_security_requirements(self, path: str, operation: str) -> list[dict]:
        """
        Get the security requirements of an endpoint.
        """
        endpoint_def = self.paths[path][operation]
        if "security" in endpoint_def.keys():
            return endpoint_def["security"]

        # Fall back to default security requirements if they exist
        elif "security" in self.definition.keys():
            return self.definition["security"]

        return []

    def requires_auth(self, path: str, operation: str) -> bool:
        """
        Check whether an endpoint requires authentication or authorization for access.
        """
        endpoint_reqs = self.get_security_requirements(path, operation)

        return len(endpoint_reqs) > 0

    def get_param_defs(self, path: str, operation: str, required_only: bool = False) -> dict[str, dict]:
        """
        Get the parameter  definitions for an endpoint.
        """
        path_def = self.paths[path]
        endpoint_def = path_def[operation]
        params = {}

        # Path parameters
        if "parameters" in path_def.keys():
            for param in path_def["parameters"]:
                if "$ref" in param.keys():
                    param = self.resolve_ref(param["$ref"])

                if required_only:
                    if "required" in param.keys() and param["required"] is True:
                        params.update({
                            param["name"]: param
                        })
                else:
                    params.update({
                        param["name"]: param
                    })

        # Endpoint parameters (overwrite path parameter definitions)
        if "parameters" in endpoint_def.keys():
            for param in endpoint_def["parameters"]:
                if "$ref" in param.keys():
                    param = self.resolve_ref(param["$ref"])

                if required_only:
                    if "required" in param.keys() and param["required"] == True:
                        params.update({
                            param["name"]: param
                        })

                    elif "required" in param.keys() and param["required"] == False:
                        params.pop(param["name"], None)
        return params

    def get_required_param_ids(self, path: str, operation: str) -> list[str]:
        """
        Get the IDs of the required parameter of an endpoint.
        """
        return list(self.get_param_defs(path, operation, required_only=True).keys())

    def requires_parameters(self, path: str, operation: str) -> bool:
        """
        Check whether an endpoint requires one or more input parameters.
        """
        endpoint_reqs = self.get_required_param_ids(path, operation)

        return len(endpoint_reqs) > 0

    def get_request_body(self, path: str, operation: str) -> dict:
        """
        Get the request body definition for a specific operation on a specific path.

        :param path: The path of the endpoint.
        :param operation: The operation (e.g., 'get', 'post') to get the request body for.
        :return: A dictionary representing the request body, or None if not defined.
        """
        if path in self.definition["paths"] and operation in self.definition["paths"][path]:
            operation_item = self.definition["paths"][path][operation]
            if "requestBody" in operation_item:
                request_body = operation_item["requestBody"]
                if "$ref" in request_body:
                    request_body = self.resolve_ref(request_body["$ref"])
                return request_body
        return {}

    def get_nosec_endpoints(self) -> dict[str, list[str]]:
        """
        Get all endpoint IDs that require no security.
        """
        endpoints = defaultdict(list)

        search_endpoints = self.endpoints
        for path_id, path in search_endpoints.items():
            for op_id, _ in path.items():
                if not self.requires_auth(path_id, op_id):
                    endpoints[path_id].append(op_id)

        return dict(endpoints)

    def get_sec_endpoints(self) -> dict[str, list[str]]:
        """
        Get all endpoint IDs that have at least one security requirement.
        """
        endpoints = defaultdict(list)

        search_endpoints = self.endpoints
        for path_id, path in search_endpoints.items():
            for op_id, _ in path.items():
                if self.requires_auth(path_id, op_id):
                    endpoints[path_id].append(op_id)

        return dict(endpoints)

    def get_param_endpoints(self) -> dict[str, list[str]]:
        """
        Get all endpoint IDs that have at least one parameter requirement.
        """
        endpoints = defaultdict(list)

        search_endpoints = self.endpoints
        for path_id, path in search_endpoints.items():
            for op_id, _ in path.items():
                if self.requires_parameters(path_id, op_id):
                    endpoints[path_id].append(op_id)

        return dict(endpoints)

    def get_noparam_endpoints(self) -> dict[str, list[str]]:
        """
        Get all endpoint IDs that require no parameter.
        """
        endpoints = defaultdict(list)

        search_endpoints = self.endpoints
        for path_id, path in search_endpoints.items():
            for op_id, _ in path.items():
                if not self.requires_parameters(path_id, op_id):
                    endpoints[path_id].append(op_id)

        return dict(endpoints)

    @property
    def components(self) -> dict:
        """
        Get the component definitions of the description.
        """
        return self.definition["components"]

    @property
    def endpoints(self) -> dict[str, dict]:
        """
        Get only the path + operation definitions of the description. Other
        fields from the PathItem object (summary, description, servers, parameters)
        are excluded.
        """
        endpoints = defaultdict(dict)

        for path_id, path in self.paths.items():
            if "$ref" in path.keys():
                # Follow reference
                path = self.resolve_ref(path["$ref"])

            for op_id, operation in path.items():
                if op_id in ("summary", "description", "servers", "parameters"):
                    continue

                endpoints[path_id].update({
                    op_id: operation
                })

        return dict(endpoints)

    @property
    def paths(self) -> dict[str, dict]:
        """
        Get the path definitions of the description.
        """
        return self.definition["paths"]

    @property
    def servers(self) -> list[dict]:
        """
        Get the server definitions of the description.
        """
        return self.definition["servers"]

    def __getitem__(self, key):
        return self.definition[key]

    def __contains__(self, key):
        return key in self.definition.keys()

    def export_to_file(self, filename: str = 'exported_openapi_spec', file_format: str = 'json'):
        try:
            with open(filename + '.' + file_format, 'w') as file:
                if file_format == 'json':
                    json.dump(self.definition, file, indent=2)

                if file_format == 'yaml':
                    yaml.dump(self.definition, file)
        except (FileNotFoundError, PermissionError, OSError):
            pass

    def export_to_text(self, file_format: str = 'json') -> str:
        if file_format == 'json':
            return json.dumps(self.definition, indent=2)

        if file_format == 'yaml':
            return yaml.dump(self.definition, default_flow_style=False)

    def add_path(self, path: str, path_details=None) -> None:
        """
        Add a new path to the OpenAPI specification. If the path already exists,
        check if there is an operation that is not specified in the path in the
        specification and add it using the add_operation method. Otherwise, do nothing.

        :param path: The path to be added.
        :type path: str
        :param path_details: Details of the path containing operations and other fields.
        :type path_details: dict
        """

        # Check if the path already exists
        if path_details is None:
            path_details = {}

        if path not in self.definition["paths"]:
            self.definition["paths"][path] = path_details
        else:
            # If the path exists, add missing operations
            existing_operations = self.definition["paths"][path].keys()
            provided_operations = path_details.keys()

            for operation in provided_operations:
                if operation not in existing_operations:
                    self.add_operation(path, operation, path_details[operation])

    def add_operation(self, operation: str, path: str, operation_details: dict = None) -> None:
        """
        Add a new operation (endpoint) to a specified path.

        :param path: The path where the operation will be added.
        :type path: str
        :param operation: The HTTP method (e.g., get, post).
        :type operation: str
        :param operation_details: Details of the operation.
        :type operation_details: dict
        """
        if operation_details is None:
            operation_details = {}

        if path not in self.definition["paths"]:
            self.add_path(path)
        self.definition["paths"][path][operation] = operation_details

        # param: {name: str, in_: str, required: bool, schema: dict,description: str = ""}

    def add_parameter(self, param_details: dict, operation: str, path: str) -> None:
        """
        Add a new parameter to a specified operation.

        :param param_details:
        :param operation: The HTTP method (e.g., get, post).
        :type operation: str
        :param path: The path where the operation is located.
        :type path: str
        """

        if path not in self.definition["paths"] or operation not in self.definition["paths"][path]:
            self.add_operation(operation=operation, path=path)
        self.definition["paths"][path][operation]["parameters"].append(param_details)

    def add_request_body(self, path: str, operation: str, request_body_details: dict) -> None:
        """
        Add or update a request body specification for a specific operation of a path.

        :param path: The path where the operation is located.
        :type path: str
        :param operation: The HTTP method (e.g., get, post) of the operation.
        :type operation: str
        :param request_body_details: Details of the request body to be added or updated.
        :type request_body_details: dict
        """
        # if the path or operation do not exist, initialize them
        if path not in self.definition["paths"] or operation not in self.definition["paths"][path]:
            self.add_operation(operation=operation, path=path)

        # If requestBody already exists, update it with new details
        if "requestBody" in self.definition["paths"][path][operation]:
            self.definition["paths"][path][operation]["requestBody"].update(request_body_details)
        else:
            # Add the request body details to the operation
            self.definition["paths"][path][operation]["requestBody"] = request_body_details

    #  response_details:{status_code: str, description: str, content: dict}
    def add_response(self, path: str, operation: str, response_details: dict) -> None:
        """

        :param path:
        :param operation:
        :param response_details:
        :return:
        """

        if path not in self.definition["paths"] or operation not in self.definition["paths"][path]:
            self.add_operation(operation=operation, path=path)
        if "responses" not in self.definition["paths"][path][operation]:
            self.definition["paths"][path][operation]["responses"] = {}
        self.definition["paths"][path][operation]["responses"].append(response_details)

    def add_security_scheme(self, scheme_name: str, scheme_details: dict) -> None:
        """
        Add or update a security scheme in the OpenAPI specification.

        :param scheme_name: The name of the security scheme.
        :type scheme_name: str
        :param scheme_details: Details of the security scheme.
        :type scheme_details: dict
        """

        if "components" not in self.definition:
            self.definition["components"] = {}
        if "securitySchemes" not in self.definition["components"]:
            self.definition["components"]["securitySchemes"] = {}

        # Check if the scheme already exists and has the same details
        if scheme_name in self.definition["components"]["securitySchemes"]:
            existing_details = self.definition["components"]["securitySchemes"][scheme_name]
            if existing_details != scheme_details:
                # Update the existing scheme with new details
                self.definition["components"]["securitySchemes"][scheme_name].update(scheme_details)
        else:
            # Add the new scheme
            self.definition["components"]["securitySchemes"][scheme_name] = scheme_details

    def add_security_to_operation(self, security: list[dict], operation: str, path: str) -> None:
        """
        Adds or appends security requirements specific to a given operation of a path
        :param security:
        :param operation:
        :param path:
        :return:
        """

        # Iterate over each security requirement
        for req in security:
            for scheme_name, scheme_scopes in req.items():
                if scheme_name not in self.definition["components"]["securitySchemes"]:
                    raise SecuritySchemeNotFound(f"Security scheme '{scheme_name}' is not defined in the components.")

        if path not in self.definition["paths"] or operation not in self.definition["paths"][path]:
            self.add_operation(operation=operation, path=path)
        if "security" not in self.definition["paths"][path][operation]:
            self.definition["paths"][path][operation]["security"] = {}
        self.definition["paths"][path][operation]["security"].append(security)

    def add_security(self, security: list[dict]) -> None:
        """
        adds or appends general security requirements to the specification for all paths and operations
        :param security:
        :return:
        """

        for req in security:
            for scheme_name, scheme_scopes in req.items():
                if scheme_name not in self.definition["components"]["securitySchemes"]:
                    raise SecuritySchemeNotFound(f"Security scheme '{scheme_name}' is not defined in the components.")
        if "security" not in self.definition:
            self.definition["security"] = {}
        self.definition["security"].append(security)
