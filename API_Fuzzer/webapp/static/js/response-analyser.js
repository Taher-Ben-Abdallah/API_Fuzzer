//Initialising the interface socket
const analyserSocket = new Socket('/response-analyser');

const itemIdMapping = {
  item1: 'item1',
  item2: 'item2',
};

//SENDING
document
  .getElementById('analyseResponseBtn')
  .addEventListener('click', function (event) {
    event.preventDefault();

    data = {
      response_content: document.getElementById('responseContentTextarea')
        .value,
    };
    console.log(data);

    analyserSocket.emitMessage('start_analysis', data);
  });

//RECEIVING
analyserSocket.onMessage('analysis_result', function (data) {
  document.querySelectorAll('.analysis-info').forEach((item) => {
    item.style.display = 'block';
  });

  if (data.hasOwnProperty('result') && data.result) {
    console.log(data);
    displayResults(data.result);
    // put each result into respective item
    //Object.keys(data.result).forEach((key) => {addSpanToListItem(itemIdMapping[key], data.result[key]);});
  } else {
    console.log('The result is empty or does not exist.');
  }
});

// Function to display analysis results
function displayResults(results) {
  // Mapping results to HTML elements based on presence of results
  if (results.length_in_bytes) {
    document.getElementById('bytesInfo').querySelector('.badge').textContent =
      results.length_in_bytes;
    document.getElementById('bytesInfo').style.display = 'flex';
  }

  if (results.length_in_chars) {
    document.getElementById('charsInfo').querySelector('.badge').textContent =
      results.length_in_chars;
    document.getElementById('charsInfo').style.display = 'flex';
  }

  if (results.length_in_words) {
    document.getElementById('wordsInfo').querySelector('.badge').textContent =
      results.length_in_words;
    document.getElementById('wordsInfo').style.display = 'flex';
  }

  if (results.length_in_lines) {
    document.getElementById('linesInfo').querySelector('.badge').textContent =
      results.length_in_lines;
    document.getElementById('linesInfo').style.display = 'flex';
  }

  // Handle sensitive information
  if (results.sensitive_information.length > 0) {
    const contentBadges = document.getElementById('contentBadges');
    contentBadges.innerHTML = ''; // Clear existing badges
    results.sensitive_information.forEach((contentItem) => {
      const span = document.createElement('span');
      span.classList.add('badge', 'bg-light-primary', 'ms-1');
      span.textContent = contentItem;
      contentBadges.appendChild(span);
    });
    document.getElementById('contentInfo').style.display = 'flex';
  }

  // Handle server info
  if (results.server_info) {
    document.getElementById('serverType').textContent =
      results.server_info.type;
    document.getElementById('serverVersion').textContent =
      results.server_info.version;
    document.getElementById('serverInfo').style.display = 'flex';
  }

  // Handle authentication
  if (results.authentication && results.authentication.technique) {
    document.getElementById('authTechnique').textContent =
      results.authentication.technique;
    document.getElementById('authInfo').style.display = 'flex';
  }

  // Handle security measures
  if (results.security_measures.length > 0) {
    const securityBadges = document.getElementById('securityBadges');
    securityBadges.innerHTML = ''; // Clear existing badges
    results.security_measures.forEach((measure) => {
      const span = document.createElement('span');
      span.classList.add('badge', 'bg-light-primary', 'ms-1');
      span.textContent = measure;
      securityBadges.appendChild(span);
    });
    document.getElementById('securityMeasures').style.display = 'flex';
  }

  // Handle rate limiting
  if (results.rate_limiting) {
    if (results.rate_limiting.limit) {
      document.getElementById(
        'rateLimit'
      ).textContent = `Limit: ${results.rate_limiting.limit}`;
    }
    if (results.rate_limiting.remaining) {
      document.getElementById(
        'rateRemaining'
      ).textContent = `Remaining: ${results.rate_limiting.remaining}`;
    }
    if (results.rate_limiting.remaining) {
      document.getElementById(
        'rateReset'
      ).textContent = `Reset: ${results.rate_limiting.reset_time}`;
    }

    document.getElementById('rateLimiting').style.display = 'flex';
  }
}
