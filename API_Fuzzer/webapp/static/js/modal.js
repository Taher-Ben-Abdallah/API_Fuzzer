// Define modal content, titles, and button texts mapped to modalId
const modalContentMap = {
  confirmationModal: {
    title: 'Confirmation Required',
    content: `<p>Are you sure you want to proceed with this action?</p>`,
    actionButtonText: 'Confirm',
  },
  modal2: {
    title: 'Form Submission',
    content: `
                <form>
                    <div class="mb-3">
                        <label for="inputName" class="form-label">Name</label>
                        <input type="text" class="form-control" id="inputName" placeholder="Enter your name">
                    </div>
                    <div class="mb-3">
                        <label for="inputEmail" class="form-label">Email</label>
                        <input type="email" class="form-control" id="inputEmail" placeholder="Enter your email">
                    </div>
                </form>`,
    actionButtonText: 'Submit',
  },
  modal3: {
    title: 'Information',
    content: `<p>This is some informational content displayed inside the modal.</p>`,
    actionButtonText: 'OK',
  },
  addWordlistModal: {
    title: 'Add Wordlist',
    content: `
    <form>
        <div class="mb-3">
            <label for="wordlistFileInput" class="form-label">Include file</label>
            <input class="form-control" type="file" id="wordlistFileInput" />
        </div>
    </form>`,
    actionButtonText: 'Add',
  },
  wordlistContentModal: {
    title: 'Wordlist Content',
    content: `
    <div class="form-group with-title mb-3">
        <textarea class="form-control" id="wordlistContentTextarea" rows="10" spellcheck="false"></textarea>
    </div>
    `,
    actionButtonText: 'Ok',
  },
  wordlistSaveModal: {
    title: 'Save Wordlist',
    content: `
      <div class="form-group mb-4">
        <label for="savedWordlistNameInput">Saved Wordlist Name</label>
        <input type="text" class="form-control" id="savedWordlistNameInput" placeholder="saved_wordlist.txt">
      </div>
    `,
    actionButtonText: 'Save',
  },
  // Config Modals
  loadConfigModal: {
    title: 'Load Configuration from file',
    content: `
    <form>
        <div class="mb-3">
            <label for="configFileInput" class="form-label">Load file content</label>
            <input class="form-control" type="file" id="configFileInput"/>
        </div>
    </form>`,
    actionButtonText: 'Load',
  },
  setProxyModal: {
    title: 'Set Proxy ',
    content: `
  <form>
      <div class="mb-3">
          <label for="setProxyInput" class="form-label">Proxy address</label>
          <input class="form-control" type="text" id="setProxyInput"/>
      </div>
  </form>`,
    actionButtonText: 'Set',
  },
  // SESSION
  createSessionModal: {
    title: 'Create a session',
    content: `
      <label for="sessionNameInput" class="form-label">Session Name</label>
      <input type="text" class="form-control" id="sessionNameInput" placeholder="Enter session name">
  `,
    actionButtonText: 'Start session',
  },
  loadSessionModal: {
    title: 'Load a session',
    content: `
      <label for="sessionFileInput" class="form-label">Select Session File</label>
      <input type="file" class="form-control" id="loadSessionFileInput">
  `,
    actionButtonText: 'Load',
  },

  // Ratelimiting Modal
  rateLimitModal: {
    title: 'Set Rate and concurrency limits',
    content: `    
      <div class="px-4">
          <label for="helperText">Request Rate limit</label>
          <input type="text" id="rateLimitInput" class="form-control" placeholder="150">
          <p><small class="text-muted">Number of requests per second</small></p>
      </div>
      <div class="px-4">
          <label for="helperText">Concurrency limit</label>
          <input type="text" id="concurrencyLimitInput" class="form-control" placeholder="10">
          <p><small class="text-muted">Number of simultaneous requests sent </small></p>
      </div>

    `,
    actionButtonText: 'Set Limit',
  },
  //Response Analysis Modals
  matchHideModal: {
    title: 'Match or Hide requests',
    content: `
    <div class="row px-5 mb-3">
      <select class="form-select" id="matchHideModeSelect">
        <option value="match">Match</option>
        <option value="hide">Hide</option>
      </select>
    </div>
    <div class="px-5" id="matchHideContentContainer" style="max-height: 300px; overflow-y: auto;">
      <!-- Container for dynamically added form groups -->
    </div>
    <div class="row px-5">
      <button id="addMatchHideGroupBtn" class="btn btn-light"><b>+</b></button>
    </div>
    `,
    actionButtonText: 'Set',
  },
  analyseResponseModal: {
    title: 'Analyse response content',
    content: `
    
    `,
    actionButtonText: 'Add',
  },
};

//FUNCTION SHOWMODAL
function showModal(modalId, callbackFunction) {
  //create modal once
  if (document.getElementById(modalId)) {
    return;
  }

  // Get the modal data based on the modalId
  const modalData = modalContentMap[modalId];

  if (!modalData) {
    console.error('No modal data found for ID:', modalId);
    return;
  }

  // Create the modal structure
  const modalHTML = `
        <div class="modal modal-borderless fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="${modalId}Label">${modalData.title}</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
              </div>
              <div class="modal-body">
                ${modalData.content}
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                <button type="button" class="btn btn-primary" id="${modalId}ActionBtn" data-bs-dismiss="modal">${modalData.actionButtonText}</button>
              </div>
            </div>
          </div>
        </div>`;

  // Append the modal to the body
  document.body.insertAdjacentHTML('beforeend', modalHTML);

  // Set up the modal using Bootstrap's API
  const modalElement = document.getElementById(modalId);
  const modalInstance = new bootstrap.Modal(modalElement);

  // Show the modal
  modalInstance.show();

  // Add the callback to the action button
  const actionButton = document.getElementById(`${modalId}ActionBtn`);
  if (actionButton) {
    actionButton.addEventListener('click', function () {
      callbackFunction();
    });
  }

  // Remove the modal from DOM after it's hidden to prevent accumulation
  modalElement.addEventListener('hidden.bs.modal', function () {
    modalElement.remove();
  });
}
