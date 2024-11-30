//Initialising the interface socket
const mergeWordlistsSocket = new Socket('/merge-wordlists');

let wordlistsList = [];

// Emit the 'start_merge' event
document.getElementById('mergeBtn').addEventListener('click', function (event) {
  event.preventDefault();

  data = {
    wordlists: wordlistsList.map((wordlist) => wordlist.content),
    merge_type: document.getElementById('mergeTypeSelect').value,
  };
  if (
    ['zip', 'product'].includes(
      document.getElementById('mergeTypeSelect').value
    )
  ) {
    data.separator = document.getElementById('mergeSeparatorSelect').value;
  }

  console.log(data);

  mergeWordlistsSocket.emitMessage('start_merge', data);
});

// Emit the 'save_merged_wordlist' event with wordlist data
document
  .getElementById('saveWordlistBtn')
  .addEventListener('click', function (event) {
    event.preventDefault();

    const mergedWordlistsContent = document.getElementById(
      'mergedWordlistsResultTextarea'
    ).value;

    if (mergedWordlistsContent) {
      console.log('Saving merged wordlist...');
      showModal('wordlistSaveModal', function () {
        const mergedWordlistsFilename = document.getElementById(
          'savedWordlistNameInput'
        ).value;

        saveTextAsFile(mergedWordlistsContent, mergedWordlistsFilename);

        /*
        mergeWordlistsSocket.emitMessage('save_merged_wordlist', {
          wordlistName: document.getElementById('savedWordlistNameInput').value,
          wordlist: mergedWordlists,
        });*/
      });
    } else {
      console.log('No wordlist to save');
    }
  });

mergeWordlistsSocket.onMessage('merge_result', function (data) {
  console.log('Merge result received:', data);
  //check result
  if (data.hasOwnProperty('result') && data.result) {
    document.getElementById('mergedWordlistsResultTextarea').value =
      data.result;
  } else {
    console.log('The result is empty or does not exist.');
  }
});

// Listen for 'wordlist_save' event and handle the response
mergeWordlistsSocket.onMessage('wordlist_save_status', function (data) {
  console.log('Wordlist save result received:', data);
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
