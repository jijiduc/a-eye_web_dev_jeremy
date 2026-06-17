/**
 * JS worker for inspecting .zip/.7z archive contents in the counting cases process.
 */

importScripts('/static/js/js7z/js7z.js');

self.onmessage = async function (event) {
    const { id, name, buffer } = event.data;
    const unzipped = [];
    const js7z = await JS7z({
        // Emscripten hook
        locateFile: (path) => '/static/js/js7z/' + path,
        print: (line) => unzipped.push(line),
        printErr: (line) => unzipped.push(line),
    });

    js7z.onExit = (code) => {
        if (code === 0) {
            // success is code = 0
            self.postMessage({ id, paths: parsePaths(unzipped) });
        } else {
            // error handling
             self.postMessage({ id, error: '[js7z] Error during archive unzipping...' });
        }
    };
    js7z.onAbort = (cause) => {
      self.postMessage({ id, error: `[js7z] Process aborted: ${cause}` });
  };


    // Using Emscripten as part of js7z, writing the files in
    js7z.FS.mkdir('/in');
    js7z.FS.writeFile('/in/' + name, new Uint8Array(buffer));
    js7z.callMain(['l', '-slt', '/in/' + name])

};

// Extracting the files path
function parsePaths(lines) {
    const paths = [];

    for (const line of lines) {
        if (line.startsWith('Path = ')) {
            paths.push(line.replace('Path = ', '').trim());
        }
    }
    // slice(0) is the archive itself - so ignored
    return paths.slice(1);
}