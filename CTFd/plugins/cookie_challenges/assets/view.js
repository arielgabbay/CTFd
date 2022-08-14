CTFd._internal.challenge.data = undefined;

// TODO: Remove in CTFd v4.0
CTFd._internal.challenge.renderer = null;

CTFd._internal.challenge.preRender = function() {};

// TODO: Remove in CTFd v4.0
CTFd._internal.challenge.render = null;

CTFd._internal.challenge.postRender = function() {};

CTFd._internal.challenge.submit = function(preview) {
  var challenge_id = parseInt(CTFd.lib.$("#challenge-id").val());
  var submission = CTFd.lib.$("#challenge-input").val();

  var body = {
    challenge_id: challenge_id,
    submission: submission
  };
  var params = {};
  if (preview) {
    params["preview"] = true;
  }

  return CTFd.api.post_challenge_attempt(params, body).then(function(response) {
    if (response.status === 429) {
      // User was ratelimited but process response
      return response;
    }
    if (response.status === 403) {
      // User is not logged in or CTF is paused.
      return response;
    }
    return response;
  });
};

function encodeHex(hex) {
    for (var bytes = [], c = 0; c < hex.length; c += 2)
        bytes.push(parseInt(hex.substr(c, 2), 16));
    for (var output = [], i = 0; i < bytes.length; i++) {
      var current = bytes[i] < 0 ? bytes[i] + 256 : bytes[i];
      output.push("%");
      output.push((current >>> 4).toString(16));
      output.push((current & 0xF).toString(16));
    }
    return output.join("");
}

function downloadFlag(flag) {
  var element = document.createElement('a');
  element.setAttribute('href', 'data:application/octet-stream;charset=utf-8,' + encodeHex(flag));
  element.setAttribute('download', "enc.bin");

  element.style.display = 'none';
  document.body.appendChild(element);

  element.click();

  document.body.removeChild(element);
}
