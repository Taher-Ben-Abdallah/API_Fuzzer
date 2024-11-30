function getFileData(file, callback) {
  const reader = new FileReader();

  // Event listener for when the file is read
  reader.onload = function (event) {
    const fileContent = event.target.result; // Get file content

    // Pass the file data to the callback
    callback({
      filename: file.name,
      content: fileContent,
    });
  };

  // Trigger event
  reader.readAsText(file);
}

function saveTextAsFile(textContent, filename) {
  // Create a Blob with the text content and specify the MIME type as plain text
  const blob = new Blob([textContent], { type: 'text/plain' });

  // Create a temporary anchor element
  const link = document.createElement('a');

  // Ensure filename has .txt extension
  if (!filename.includes('.')) {
    filename += '.txt';
  } else if (!/^[^.]+\.[a-zA-Z0-9]+$/.test(filename)) {
    console.log('invalid filename: ' + filename);
  }

  // Set the download attribute with a filename
  link.download = filename;

  // Create a URL for the Blob and set it as the href attribute of the anchor
  link.href = URL.createObjectURL(blob);

  // Programmatically click the anchor to trigger the download
  link.click();

  // Clean up the URL object
  URL.revokeObjectURL(link.href);
}
