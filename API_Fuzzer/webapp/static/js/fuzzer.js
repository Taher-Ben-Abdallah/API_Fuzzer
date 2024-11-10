//Initialising the interface socket
const fuzzerSocket = new Socket('/fuzzer');

let wordlists = {};

/** MATCH HIDE MODAL CODE**/
let matchHideGroupCount = 0; // Counter to track the number of form groups

// Function to create a new form group with a select and dynamic fields
function addMatchHideGroup() {
  matchHideGroupCount++;

  const matchHideGroup = document.createElement('div');
  matchHideGroup.className = 'match-hide-group mb-5';
  matchHideGroup.id = `matchHideGroup${matchHideGroupCount}`;

  // Create the select element
  const selectElement = document.createElement('select');
  selectElement.className = 'form-select dynamic-select';
  selectElement.dataset.groupId = matchHideGroupCount; // Custom attribute to identify the group

  selectElement.innerHTML = `
        <option value="response-code">Status Code</option>
        <option value="response-header">Response Header</option>
        <option value="response-value">Content in response</option>
        <option value="elapsed-time">Elapsed Time</option>
        <option value="length-in">Response Length</option>
        <option value="sensitive-info">Sensitive information</option>
    `;

  // Create container for input fields
  const inputContainer = document.createElement('div');
  inputContainer.className = 'input-container mt-3';
  inputContainer.id = `inputContainer${matchHideGroupCount}`;

  // Append elements to the form group
  matchHideGroup.appendChild(selectElement);
  matchHideGroup.appendChild(inputContainer);
  document
    .getElementById('matchHideContentContainer')
    .appendChild(matchHideGroup);

  //make sure input field is shown when we add group
  showInputFields(this.value, inputContainer, matchHideGroupCount);
  // Add event listener to select for showing input fields
  selectElement.addEventListener('change', function () {
    showInputFields(this.value, inputContainer, matchHideGroupCount);
  });
}

// Function to show input fields based on selected option
function showInputFields(selectedValue, inputContainer, groupId) {
  // Clear any existing input fields
  inputContainer.innerHTML = '';

  // Display different input fields based on the selected value
  switch (selectedValue) {
    case 'response-code':
      inputContainer.innerHTML = `
        <label for="statusCodesInput">Status codes</label>
        <input type="text" class="form-control" id="statusCodesInput" placeholder="401,403,404">
        `;
      break;
    case 'length-in':
      inputContainer.innerHTML = `
        <select class="form-select" id="lengthInSelect">
                <option value="bytes">In Bytes</option>
                <option value="lines">In Lines</option>
                <option value="words">In Words</option>
                <option value="chars">In Chars</option>
        </select>
        <label for="lengthMaxValueInput">Max length</label>
        <input type="text" class="form-control" id="lengthMaxValueInput">
        <label for="lengthMinValueInput">Min length</label>
        <input type="text" class="form-control" id="lengthMinValueInput">
        `;
      break;
    case 'elapsed-time':
      inputContainer.innerHTML = `
        <label for="elapsedTimeMaxValueInput">Max time</label>
        <input type="text" class="form-control" id="elapsedTimeMaxValueInput">
        <label for="elapsedTimeMinValueInput">Min time</label>
        <input type="text" class="form-control" id="elapsedTimeMinValueInput">
        `;
      break;
    case 'response-value':
      inputContainer.innerHTML = `
        <label for="responseValueInput">Value in response</label>
        <input type="text" class="form-control" id="responseValueInput">
        `;
      break;
    case 'response-header':
      inputContainer.innerHTML = `
            <div class="input-group" id="responseHeaderDiv">
                <input type="text" aria-label="Key" class="form-control" id="responseHeaderKeyInput" placeholder="Key">
                <input type="text" aria-label="Value" class="form-control" id="responseHeaderValueInput" placeholder="Value">
            </div>
        `;
      break;
    case 'sensitive-info':
      inputContainer.innerHTML = `
        <select id="patternSelect" class="form-select">
            <option value="16 digits credit card numbers">16 digits credit card numbers</option>
            <option value="Credit card numbers">Credit card numbers</option>
            <option value="Social Security Numbers">Social Security Numbers</option>
            <option value="Email Addresses">Email Addresses</option>
            <option value="International phone numbers">International phone numbers</option>
            <option value="Common password patterns">Common password patterns</option>
            <option value="API Keys">API Keys</option>
            <option value="Date of birth">Date of birth</option>
        </select>
        `;
      break;
  }
}

// Function to collect all data from the form groups
function collectMatchHideData() {
  const data = [];

  const selectedMode = document.getElementById('matchHideModeSelect').value;
  document.querySelectorAll('.match-hide-group').forEach((group) => {
    const groupId = group.id.replace('matchHideGroup', '');
    let selectedOption = group.querySelector('.dynamic-select').value;

    let inputData = {};
    if (selectedOption === 'response-code') {
      const statusCodes = group.querySelector('#statusCodesInput')?.value || '';
      inputData = { code: statusCodes.split(',') };
    } else if (selectedOption === 'length-in') {
      const lengthType = group.querySelector('#lengthInSelect')?.value || '';
      selectedOption = selectedOption + '-' + lengthType;
      const maxLength =
        group.querySelector('#lengthMaxValueInput')?.value || '';
      const minLength =
        group.querySelector('#lengthMinValueInput')?.value || '';
      inputData = { max: maxLength, min: minLength };
    } else if (selectedOption === 'elapsed-time') {
      const maxTime =
        group.querySelector('#elapsedTimeMaxValueInput')?.value || '';
      const minTime =
        group.querySelector('#elapsedTimeMinValueInput')?.value || '';
      inputData = { max: maxTime, min: minTime };
    } else if (selectedOption === 'response-value') {
      const responseValue =
        group.querySelector('#responseValueInput')?.value || '';
      inputData = { value: responseValue };
    } else if (selectedOption === 'response-header') {
      const headerKey =
        group.querySelector('#responseHeaderKeyInput')?.value || '';
      const headerValue =
        group.querySelector('#responseHeaderValueInput')?.value || '';
      inputData = { headers: { headerKey: headerValue } };
    } else if (selectedOption === 'sensitive-info') {
      const pattern = group.querySelector('#patternSelect')?.value || '';
      inputData = { info: [pattern] };
    }

    data.push({
      selectedOption: inputData,
    });
  });

  console.log(data); // Log the collected data for testing
  return data;
}

function collectRateLimitData() {
  // Get the values from the input fields
  const rateLimit = document.getElementById('rateLimitInput').value;
  const concurrencyLimit = document.getElementById(
    'concurrencyLimitInput'
  ).value;

  // Store the collected data in an object
  const data = {
    rate_limit: rateLimit,
    concurrency_limit: concurrencyLimit,
  };

  console.log(data); // Log the data for testing
  return data; // Return the data object if needed
}

function getSelectedResponseInfo(checkboxesContainerId) {
  const selectedCheckboxes = document.querySelectorAll(
    `#${checkboxesContainerId} input[type="checkbox"]:checked`
  );
  const selectedResponseInfo = Array.from(selectedCheckboxes).map(
    (checkbox) => checkbox.value
  ); // Collects selected checkbox IDs
  return selectedResponseInfo; // e.g., ['responseStatusCheckbox', 'responseElapsedTimeCheckbox']
}

function requestContentToObject(requestString) {
  const requestObject = {
    method: null,
    url: null,
    queryParams: {},
    headers: {},
    body: null,
  };

  // Split the request into lines
  const lines = requestString.split('\n');
  // Extract method and URL
  const [method, urlWithParams] = lines[0].split(' ');
  requestObject.method = method;
  // Separate URL and query parameters
  const [url, queryString] = urlWithParams.split('?');
  requestObject.url = url;
  // Parse query parameters
  if (queryString) {
    queryString.split('&').forEach((param) => {
      const [key, value] = param.split('=');
      requestObject.queryParams[key] = decodeURIComponent(value || '');
    });
  }
  // Parse headers
  let i = 1;
  for (; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line === '') break; // End of headers
    const [key, value] = line.split(': ');
    if (key && value) {
      requestObject.headers[key] = value;
    }
  }

  // Remaining lines are considered the body
  const bodyLines = lines
    .slice(i + 1)
    .join('\n')
    .trim();
  if (bodyLines) {
    requestObject.body = bodyLines;
  }

  return requestObject;
}

function collectFuzzData(rateLimitData, matchHideData, proxyData) {
  let data = {};

  data.request_details = requestContentToObject(
    document.getElementById('requestContentTextarea').value
  );
  data.num_workers = document.getElementsByTagName('numWorkersInput').value;
  //fuzzing values information
  data.wordlists = wordlists;
  data.iterator = document.getElementById('iteratorTypeSelect').value;

  // analysis information
  data.analysis = getSelectedResponseInfo('includedResponseInfoContainer');
  data.match_hide = matchHideData;

  data.rate_conc_limit = rateLimitData;

  data.http_version = document
    .getElementById('requestContentTextarea')
    .value.split('\n')[0]
    .split(' ')[2];

  data.proxy = proxyData;

  return data;
}
