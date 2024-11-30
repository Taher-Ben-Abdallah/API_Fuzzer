//Initialising the interface socket
const generatorSocket = new Socket('/payload-generator');

// Emit the 'start_merge' event
document
  .getElementById('generatePayloadsBtn')
  .addEventListener('click', function (event) {
    event.preventDefault();

    data = {};
    console.log(data);

    generatorSocket.emitMessage('start_generation', data);
  });

// Emit the 'save_merged_wordlist' event with wordlist data
document
  .getElementById('savePayloadsBtn')
  .addEventListener('click', function (event) {
    event.preventDefault();

    const generatedPayloads =
      document.getElementById('payloadGenTextArea').value;

    if (generatedPayloads) {
      console.log(generatedPayloads);

      generatorSocket.emitMessage('save_generated_payloads', {
        payloads: generatedPayloads,
      });
    } else {
      console.log('No payloads to save');
    }
  });

generatorSocket.onMessage('generation_result', function (data) {
  console.log(data);
  //check result
  if (data.hasOwnProperty('result') && data.result) {
    document.getElementById('payloadGenTextArea').value = data.result;
  } else {
    console.log('The result is empty or does not exist.');
  }
});

// Listen for 'wordlist_save' event and handle the response
generatorSocket.onMessage('gen_payloads_save_status', function (data) {
  if (data.hasOwnProperty('status') && data.status) {
    if (data.status === 'success') {
      console.log('success');
    }
    if (data.status === 'error') {
      console.log('error');
    }
  }
  //document.getElementById('saveResultDisplay').textContent = data.status;
});
