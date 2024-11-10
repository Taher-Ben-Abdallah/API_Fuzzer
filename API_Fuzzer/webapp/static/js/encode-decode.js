//Initialising the interface socket
const encdecSocket = new Socket('/encode-decode');

document
  .getElementById('getResultBtn')
  .addEventListener('click', function (event) {
    event.preventDefault();
    // collect operation data
    data = {};
    data.operation = document
      .getElementById('encdecSelect')
      .value.toLowerCase();
    data.method = document.getElementById('formatSelect').value.toLowerCase();
    data.content = document.getElementById('encdecTextArea').value;
    console.log(data);

    encdecSocket.emitMessage('start_encdec', data);
  });

encdecSocket.onMessage('encdec_result', function (data) {
  if (data.hasOwnProperty('result') && data.result) {
    document.getElementById('encdecResultTextarea').value = data.result;
  } else {
    console.log('The result is empty or does not exist.');
  }
});
