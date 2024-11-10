class Socket {
  // Initialize connection
  constructor(namespace) {
    this.socket = io(`http://127.0.0.1:5000${namespace}`, {
      reconnection: true, // Enable reconnection
      reconnectionAttempts: 10, // Try 10 times
      reconnectionDelay: 1000, // Start with a 1 second delay between retries
      reconnectionDelayMax: 5000, // Maximum delay between retries
      timeout: 20000, // Timeout if connection cannot be established
    });

    // Log connection and disconnection
    this.socket.on('connect', () => {
      console.log(`Connected to core on namespace: ${namespace}`);
    });

    /*this.socket.on('disconnect', () => {
      console.log(`Disconnected from namespace: ${namespace}`);
    });
    */
  }

  // Function to handle emitting messages from the interface
  emitMessage(event, data) {
    this.socket.emit(event, data);
  }

  // Function to handle receiving messages from the interface
  onMessage(event, callback) {
    this.socket.on(event, callback);
  }
}
