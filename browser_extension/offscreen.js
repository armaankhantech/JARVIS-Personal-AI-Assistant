const BASE = 'http://127.0.0.1:31419';
const headers = {
  'Content-Type': 'application/json',
  'X-Jarvis-Token': JARVIS_BRIDGE_TOKEN
};

let busy = false;
const POLL_INTERVAL_MS = 750;
const COMMAND_TIMEOUT_MS = 20000;

async function poll() {
  if (busy) return;
  busy = true;

  try {
    const { profile = 'main' } =
      await chrome.storage.local.get('jarvisProfile');

    const response = await fetch(
      BASE + '/next?profile=' + encodeURIComponent(profile),
      { headers }
    );

    if (!response.ok) {
      throw new Error('Bridge polling HTTP ' + response.status);
    }

    const data = await response.json();

    if (data.command) {
      let timeoutId;

      try {
        const result = await Promise.race([
          chrome.runtime.sendMessage({
            type: 'JARVIS_COMMAND',
            command: data.command
          }),
          new Promise((_, reject) => {
            timeoutId = setTimeout(
              () => reject(new Error('Command response timed out')),
              COMMAND_TIMEOUT_MS
            );
          })
        ]);

        if (result?.success === false) {
          console.error('Jarvis command failed:', result.error);
        }
      } finally {
        clearTimeout(timeoutId);
      }
    }
  } catch (error) {
    console.error('Jarvis bridge polling error:', error);
  } finally {
    busy = false;
    setTimeout(poll, POLL_INTERVAL_MS);
  }
}

poll();
