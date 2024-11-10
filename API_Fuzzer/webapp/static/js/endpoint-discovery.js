//Initialising the interface socket
const discoverySocket = new Socket('/endpoint-discovery');

document
  .getElementById('uploadFileBtn')
  .addEventListener('click', function (event) {
    event.preventDefault();

    showModal('confirmationModal', function () {
      console.log('action clicked');
      const fileInput = document.getElementById('fileInput');
      const file = fileInput.files[0]; // Get the selected file

      if (file) {
        getFileData(file, function (fileData) {
          console.log(fileData);
        });
      }
    });
  });

function collectDiscoveryData(
  rateLimitData,
  matchHideData,
  proxyData
) {
  let data = {};
  data.path = document.getElementById('pathInput').value;
  data.depth = document.getElementById('depthInput').value;
  data.num_workers = document.getElementsByTagName('numWorkersInput').value;
  data.match_hide = matchHideData;
  data.rate_conc_limit = rateLimitData;
  data.proxy = proxyData;

  return data;
}
