//Initialising the interface socket
const configSocket = new Socket('/configuration');

document
  .getElementById('applyConfigBtn')
  .addEventListener('click', function (event) {
    event.preventDefault();

    // collect operation data
    let data = { config: collectConfig() };

    configSocket.emitMessage('apply_conf', data);
  });

configSocket.onMessage('apply_conf_status', function (data) {
  console.log(data);

  if (data.hasOwnProperty('status') && data.status) {
    if (data.status === true) {
      console.log('success');
    }
    if (data.status === false) {
      console.log('error');
    }
  }
});

// Collect form data and configuration editor content when the Apply Configuration button is clicked
function collectConfig() {
  // Collect configuration editor content if visible
  let config = '';
  if (isConfigEditorVisible) {
    config = document.getElementById('configEditorTextArea').value;
  } else {
  }

  const proxy = document.getElementById('proxyConfigInput').value;

  // Create the configuration object
  const configData = JSON.stringify({
    fuzz_engine: {
      workers: document.getElementById('workersConfigInput').value,
      rate_limit: document.getElementById('rateLimitConfigInput').value,
      concurrency_limit: document.getElementById('concurrencyConfigInput')
        .value,
      timeout: document.getElementById('timeoutConfigInput').value,
    },
    request: {
      headers: parseTextAreaToObject(
        document.getElementById('headersConfigInput').value
      ),
      cookies: document.getElementById('cookiesConfigInput').value,
      parameters: parseTextAreaToObject(
        document.getElementById('paramsConfigTextArea').value,
        '='
      ),
    },
    analysis: {},
    match_hide: {},

    //proxy: proxy,
  });

  console.log(configData); // Replace with actual usage of the collected data
  return config;
}

function parseTextAreaToObject(text, sep = ':') {
  const lines = text.split('\n');
  const result = {};

  lines.forEach((line) => {
    const [key, value] = line.split(sep); // Split each line by the colon
    if (key && value !== undefined) {
      // Ensure both key and value are present
      result[key.trim()] = value.trim();
    }
  });

  return result;
}
