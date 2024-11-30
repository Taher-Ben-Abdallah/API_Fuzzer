//Initialising the interface socket
const requesterSocket = new Socket('/requester');

function createRequestString(requestData) {
  // Parse the JSON string data
  const data = JSON.parse(requestData);

  // Start with the method and URL
  let requestString = `${data.method.toUpperCase()} ${data.url}`;

  // Append query parameters to the URL if they exist
  const queryParams = new URLSearchParams(data.params).toString();
  if (queryParams) {
    requestString += `?${queryParams}`;
  }
  requestString += ' HTTP/1.1\n';

  // Add headers
  if (data.headers) {
    for (const [key, value] of Object.entries(data.headers)) {
      requestString += `${key}: ${value}\n`;
    }
  }

  // Add authentication information
  if (data.auth) {
    switch (data.auth.type) {
      case 'basic':
        // Basic Auth requires base64 encoding of username:password
        const basicAuth = btoa(`${data.auth.username}:${data.auth.password}`);
        requestString += `Authorization: Basic ${basicAuth}\n`;
        break;

      case 'bearer':
        requestString += `Authorization: Bearer ${data.auth.token}\n`;
        break;

      case 'digest':
        // Digest Auth may involve more complexity and nonce handling
        // This is a placeholder and would be more complex in actual use
        const digestAuth = btoa(`${data.auth.username}:${data.auth.password}`);
        requestString += `Authorization: Digest ${digestAuth}\n`;
        break;

      case 'apiKey':
        requestString += `${data.auth.key}\n`;
        break;

      case 'jwt':
        if (data.auth.action === 'generate-jwt') {
          // Generating JWT tokens would require a library (e.g., jsonwebtoken)
          // Here, we’ll mock it as if the JWT is generated
          const jwtToken = 'mockGeneratedToken123'; // Replace with actual JWT generation
          requestString += `Authorization: Bearer ${jwtToken}\n`;
        } else if (data.auth.action === 'use-jwt') {
          requestString += `Authorization: Bearer ${data.auth.token_info}\n`;
        }
        break;

      case 'ntlm':
        const ntlmAuth = `${data.auth.domain}\\${data.auth.username}:${data.auth.password}`;
        requestString += `Authorization: NTLM ${btoa(ntlmAuth)}\n`;
        break;

      case 'custom':
        requestString += `${data.auth.header_key}: ${data.auth.header_value}\n`;
        break;
    }
  }

  // Add Content-Type based on body format if provided
  if (data.content && data.content.format) {
    const contentType =
      {
        json: 'application/json',
        xml: 'application/xml',
        text: 'text/plain',
        form: 'application/x-www-form-urlencoded',
      }[data.content.format] || 'text/plain';

    requestString += `Content-Type: ${contentType}\n`;

    // Add body content if it exists
    if (data.content.body) {
      requestString += `\n${data.content.body}`;
    }
  }

  return requestString;
}
